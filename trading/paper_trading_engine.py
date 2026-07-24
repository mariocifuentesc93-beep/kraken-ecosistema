"""Persistent paper trading driven by read-only market data; no MT5 order API is used."""
from datetime import datetime
from hashlib import sha256

from repositories.paper_trading_repository import paper_trading_repository
from services.market_data_service import market_data_service
from trading.execution_pipeline import execution_pipeline


class PaperTradingEngine:
    CONTRACT_SIZE = 100.0

    def configure(self, profile_id, **values):
        account = paper_trading_repository.account(profile_id)
        for key in ("starting_balance", "currency", "slippage", "commission", "allow_fallback"):
            if key in values: account[key] = values[key]
        if account["balance"] == account["starting_balance"]: account["equity"] = account["starting_balance"]
        return paper_trading_repository.save_account(account)

    def reset(self, profile_id): return paper_trading_repository.reset(profile_id)

    @staticmethod
    def _signal_key(signal):
        value = getattr(signal, "id", None) or f"{getattr(signal,'chat_id', '')}:{getattr(signal,'message_id','')}:{signal.symbol}:{signal.direction}:{signal.entry}"
        return sha256(str(value).encode()).hexdigest()

    def execute(self, signal, profile, mt5_account=None, quote=None):
        account = paper_trading_repository.account(profile.id)
        key = self._signal_key(signal)
        if paper_trading_repository.by_signal(key): return None
        quote = quote or market_data_service.quote(signal.symbol, allow_fallback=bool(account["allow_fallback"]))
        if not quote.get("available") or not quote.get("fresh") or (quote.get("source") == "FALLBACK" and not account["allow_fallback"]):
            return self._create_rejected(account, key, signal, profile, quote)
        if not self._risk_valid(profile): return self._create_rejected(account, key, signal, profile, quote)
        operation = execution_pipeline.create(signal, profile, mt5_account, "PAPER")
        execution_pipeline.transition(operation, "QUEUED", "Paper trade en cola", "PAPER")
        buy = signal.direction.upper() == "BUY"; base = quote["ask"] if buy else quote["bid"]
        entry = float(signal.entry or base); pending = bool(signal.entry) and not signal.market_execution
        volume, risk = self._sizing(profile, account, entry, signal.stop_loss)
        spread = abs(quote["ask"] - quote["bid"]) * volume * self.CONTRACT_SIZE
        slip = float(account["slippage"]) * volume * self.CONTRACT_SIZE
        trade = {"paper_account_id":account["id"],"operation_id":operation.id,"signal_key":key,"profile_id":profile.id,"symbol":signal.symbol,"direction":signal.direction,"status":"PENDING" if pending else "OPEN","volume":volume,"remaining_volume":volume,"entry_price":None if pending else base + (account["slippage"] if buy else -account["slippage"]),"stop_loss":signal.stop_loss,"take_profits":list(signal.take_profits),"gross_pl":0,"spread_cost":spread,"slippage_cost":slip,"commission_cost":float(account["commission"])*volume,"net_pl":0,"initial_risk":risk,"margin_estimate":entry*volume*self.CONTRACT_SIZE/100,"opened_at":None if pending else datetime.now().isoformat(),"closed_at":None,"duration_seconds":0,"updated_at":datetime.now().isoformat(),"metadata":{"break_even":False,"trailing":False,"partial_count":0,"requested_entry":signal.entry if pending else 0,"initial_risk_price":abs(entry-float(signal.stop_loss or entry))}}
        trade["metadata"]["tp1_management"] = getattr(
            profile, "tp1_management", "PROTECT_TP1"
        )
        return paper_trading_repository.create_trade(trade)

    def process_price(self, trade_id, quote):
        trade=paper_trading_repository.get_trade(trade_id)
        if not trade or trade["status"] not in ("PENDING","OPEN"): return trade
        buy=trade["direction"].upper()=="BUY"; price=quote["ask"] if buy else quote["bid"]
        if trade["status"]=="PENDING":
            entry=float(trade["metadata"].get("requested_entry",0) or trade["entry_price"] or 0)
            # Requested entry is stored on creation below; zero means market.
            requested=trade["metadata"].get("requested_entry", 0)
            if requested and ((buy and price>requested) or (not buy and price<requested)): return trade
            trade["status"]="OPEN"; trade["entry_price"]=price; trade["opened_at"]=datetime.now().isoformat()
        stop=trade["stop_loss"]
        if stop and ((buy and price<=stop) or (not buy and price>=stop)): return self._close(trade, price, "SL")
        targets=trade["take_profits"]
        for index,target in enumerate(targets[:3],1):
            if trade["metadata"].get(f"tp{index}") or not ((buy and price>=target) or (not buy and price<=target)): continue
            trade["metadata"][f"tp{index}"] = True
            tp1_management = trade["metadata"].get("tp1_management", "PROTECT_TP1")
            if (
                index in (1, 2)
                and index < len(targets[:3])
                and tp1_management == "PROTECT_TP1"
            ):
                # Keep the full position open for TP2/TP3 while locking profit.
                trade["stop_loss"] = float(target)
                trade["metadata"][f"tp{index}_protected"] = True
                if index == 2:
                    trade["metadata"]["trailing"] = True
                continue
            portion=trade["remaining_volume"] if index==len(targets[:3]) else trade["volume"]/3
            self._realize(trade, price, min(portion,trade["remaining_volume"])); trade["metadata"]["partial_count"]+=1
            if index==1: trade["stop_loss"]=trade["entry_price"]; trade["metadata"]["break_even"]=True
            if index==2: trade["metadata"]["trailing"]=True
            if trade["remaining_volume"]<=0: return self._close(trade, price, f"TP{index}", already_realized=True)
        if trade["metadata"].get("trailing"):
            risk=trade["metadata"].get("initial_risk_price", 0)
            candidate=price-risk if buy else price+risk
            trade["stop_loss"]=max(trade["stop_loss"],candidate) if buy else min(trade["stop_loss"],candidate)
        return paper_trading_repository.save_trade(trade)

    def cancel(self, trade_id):
        trade=paper_trading_repository.get_trade(trade_id)
        if trade and trade["status"]=="PENDING": trade["status"]="CANCELLED"; return paper_trading_repository.save_trade(trade)
        return trade
    def expire(self, trade_id):
        trade=paper_trading_repository.get_trade(trade_id)
        if trade and trade["status"]=="PENDING": trade["status"]="EXPIRED"; return paper_trading_repository.save_trade(trade)
        return trade
    def _create_rejected(self, account,key,signal,profile,quote):
        return paper_trading_repository.create_trade({"paper_account_id":account["id"],"operation_id":None,"signal_key":key,"profile_id":profile.id,"symbol":signal.symbol,"direction":signal.direction,"status":"REJECTED","volume":0,"remaining_volume":0,"entry_price":None,"stop_loss":signal.stop_loss,"take_profits":[],"gross_pl":0,"spread_cost":0,"slippage_cost":0,"commission_cost":0,"net_pl":0,"initial_risk":0,"margin_estimate":0,"opened_at":None,"closed_at":datetime.now().isoformat(),"duration_seconds":0,"updated_at":datetime.now().isoformat(),"metadata":{"reason":quote.get("stale_reason","risk")}})
    def _sizing(self, profile, account, entry, stop):
        distance=max(abs(entry-float(stop or entry)),.01); budget=account["balance"]*float(profile.risk_percent)/100 if profile.risk_mode=="PERCENT" else float(profile.risk_amount or profile.fixed_lot*distance*self.CONTRACT_SIZE)
        volume=max(float(profile.min_lot),min(float(profile.max_lot),budget/(distance*self.CONTRACT_SIZE))); return round(volume,4),round(budget,2)
    @staticmethod
    def _risk_valid(profile): return profile.risk_enabled and profile.risk_percent>0 and profile.max_open_trades>0
    def _realize(self,trade,price,volume):
        sign=1 if trade["direction"].upper()=="BUY" else -1; trade["gross_pl"]+=round((price-trade["entry_price"])*sign*volume*self.CONTRACT_SIZE,2); trade["remaining_volume"]-=volume
    def _close(self,trade,price,result,already_realized=False):
        if not already_realized: self._realize(trade,price,trade["remaining_volume"])
        trade["status"]="CLOSED"; trade["closed_at"]=datetime.now().isoformat(); trade["duration_seconds"]=(datetime.fromisoformat(trade["closed_at"])-datetime.fromisoformat(trade["opened_at"])).total_seconds() if trade["opened_at"] else 0; trade["metadata"]["result"]=result; trade["net_pl"]=round(trade["gross_pl"]-trade["spread_cost"]-trade["slippage_cost"]-trade["commission_cost"],2); trade=paper_trading_repository.save_trade(trade); account=paper_trading_repository.account(trade["profile_id"]); account["balance"]+=trade["net_pl"]; account["equity"]=account["balance"]; paper_trading_repository.save_account(account); return trade
    def summary(self,profile_id):
        account=paper_trading_repository.account(profile_id); trades=paper_trading_repository.trades(account["id"]); closed=[t for t in trades if t["status"]=="CLOSED"]; net=sum(t["net_pl"] for t in closed); return {"account":account,"open":sum(t["status"]=="OPEN" for t in trades),"pending":sum(t["status"]=="PENDING" for t in trades),"closed":len(closed),"daily_pl":round(net,2),"win_rate":round(sum(t["net_pl"]>0 for t in closed)/len(closed)*100,2) if closed else 0,"drawdown":round(max(0,account["starting_balance"]-account["equity"]),2),"trades":trades}


paper_trading_engine=PaperTradingEngine()
