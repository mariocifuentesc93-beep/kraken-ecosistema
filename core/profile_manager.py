from models.profile import Profile
from repositories.profile_repository import profile_repository


class ProfileManager:

    def create_profile(self, name, config):
        profile = Profile(
            name=name,
            description=config.get("description", "")
            if isinstance(config, dict) else "",
        )
        return profile_repository.create(profile)

    def get_profile(self, name):
        return next(
            (profile for profile in profile_repository.get_all()
             if profile.name == name),
            None,
        )

    def get_profiles(self):
        return profile_repository.get_all()

    def activate_profile(self, name):
        profile = self.get_profile(name)
        if profile is None:
            return False
        profile.active = True
        profile.enabled = True
        profile_repository.update(profile)
        return True

    def profile_exists(self, name):
        return self.get_profile(name) is not None


profile_manager = ProfileManager()
