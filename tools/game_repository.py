from models.game import CanonicalGameObject


class GameRepository:
    def __init__(self):
        self._games: dict[str, CanonicalGameObject] = {}

    def add_game(self, game: CanonicalGameObject):
        self._games[game.game_id] = game

    def get_game(self, game_id: str) -> CanonicalGameObject:
        return self._games.get(game_id)

    def update_game(self, game_id: str, **updates):
        if game_id in self._games:
            existing_game = self._games[game_id]
            updated = existing_game.model_copy(update=updates)
            self._games[game_id] = updated

    def all_games(self):
        return list(self._games.values()) 