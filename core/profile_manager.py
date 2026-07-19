from database.profile_repository import (
    save_profile,
    get_profile,
    get_profiles,
    activate_profile,
)


class ProfileManager:

    def create_profile(self, name, config):
        save_profile(name, config)
        return get_profile(name)

    def get_profile(self, name):
        return get_profile(name)

    def get_profiles(self):
        return get_profiles()

    def activate_profile(self, name):
        return activate_profile(name)

    def profile_exists(self, name):
        return get_profile(name) is not None


profile_manager = ProfileManager()