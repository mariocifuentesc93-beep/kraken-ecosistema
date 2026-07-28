from abc import ABC, abstractmethod


class MT5TerminalInstance(ABC):
    @abstractmethod
    def start(self): ...

    @abstractmethod
    def stop(self): ...

    @abstractmethod
    def status(self): ...


class MultiTerminalManager(ABC):
    @abstractmethod
    def get_instance(self, mt5_terminal_id): ...


class MT5ConnectionRegistry(ABC):
    @abstractmethod
    def connection_for(self, mt5_account_id, mt5_terminal_id): ...

    @abstractmethod
    def stop_all(self): ...


class ProfileTerminalRouter(ABC):
    @abstractmethod
    def resolve(self, profile_id): ...


class InspectorTerminalRouter(ABC):
    @abstractmethod
    def resolve_scanner(self): ...
