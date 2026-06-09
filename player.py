import random
import time
from config import LOGICAL_GRID_SIZE

class Player:
    def __init__(self, player_id, color, name):
        self.player_id = player_id
        self.color = color
        self.name = name
        self.score = 0
        self.is_ai = False

class AIPlayer(Player):
    def __init__(self, player_id, color, name, depth=3, AB=True):
        super().__init__(player_id, color, name)
        self.is_ai = True
        self.depth = depth
        self.nodes_visited = 0  # Licznik wezlow
        self.use_alpha_beta = AB # Flaga do wlaczanoa/wylaczania optymalizacji

    def evaluate_board(self, game):
        #print("Evaluation called.....")
        enemy_id = 3 - self.player_id
        score = (
            game.players[self.player_id].score * 1000
            - game.players[enemy_id].score * 300
        )

        for r in range(LOGICAL_GRID_SIZE):
            for c in range(LOGICAL_GRID_SIZE):
                cell = game.grid[r][c]

                if cell['captured']:
                    continue

                # ---------- MY DOTS ----------
                if cell['owner'] == self.player_id:
                    my_n = len(game.get_neighbors(r, c, self.player_id))
                    en_n = len(game.get_neighbors(r, c, enemy_id))

                    # shape building (but capped)
                    if my_n == 0:
                        score -= 0  #earlier 100
                    elif my_n == 1:
                        score += 150
                    elif my_n == 2:
                        score += 300
                    elif my_n >= 3:
                        score += 500
                    else:  # over-clustering penalty
                        score -= 300
                    # contact with enemy = good
                    if en_n > 0:
                        score += 100
                # ---------- ENEMY DOTS ----------
                elif cell['owner'] == enemy_id:
                    en_n = len(game.get_neighbors(r, c, enemy_id))
                    #print(game.get_neighbors(r, c, enemy_id))
                    my_n = len(game.get_neighbors(r, c, self.player_id))
                    #print("Pole:", r, c, "en=", en_n, "my=", my_n)
                    #print(game.get_neighbors(r, c, self.player_id))

                    # enemy cluster is dangerous
                    if en_n >= 3:
                        score -= 600

                    # enemy dot is being surrounded
                    if my_n >= 2 and en_n <= my_n:
                        score += 200

                    # almost trapped enemy
                    if my_n >= 3:
                        score += 500

        # small noise
        score += random.uniform(-2, 2)
        return score

    def get_move(self, game):
        self.nodes_visited = 0
        start_time = time.perf_counter()
        possible_moves = [
            (r, c)
            for r in range(LOGICAL_GRID_SIZE)
            for c in range(LOGICAL_GRID_SIZE)
            if game.grid[r][c]['owner'] == 0 and not game.grid[r][c]['captured']
        ]

        if not possible_moves:
            end_time = time.perf_counter()
            print(f"Gracz: {self.color} | Czas ruchu: {end_time - start_time:.4f} s | Odwiedzone węzły: {self.nodes_visited}")
            return None
        
        enemy_id = 3 - self.player_id

        capture_moves = []
        current_score = game.players[self.player_id].score

        for r, c in possible_moves:
            snap = game.snapshot()
            
            game.grid[r][c]['owner'] = self.player_id
            game.check_for_cycles_around(r, c)
            
            new_score = game.players[self.player_id].score
            game.restore(snap)

            if new_score > current_score:
                capture_moves.append(((r, c), new_score))

        if capture_moves:
            capture_moves.sort(key=lambda x: x[1], reverse=True)
            return capture_moves[0][0]

        # defensive_moves = []
        # current_en_score = game.players[enemy_id].score

        # for r, c in possible_moves:
        #     snap = game.snapshot()

        #     game.grid[r][c]['owner'] = enemy_id
        #     game.check_for_cycles_around(r, c)
            
        #     if game.players[enemy_id].score > current_en_score:
        #         defensive_moves.append(((r, c), game.players[enemy_id].score))
        #     game.restore(snap)

        # if defensive_moves:
        #     defensive_moves.sort(key=lambda x: x[1], reverse=True)
        #     end_time = time.perf_counter()
        #     print(f"Gracz: {self.color} | Czas ruchu: {end_time - start_time:.4f} s | Odwiedzone węzły: {self.nodes_visited}")
        #     return defensive_moves[0][0]

        if random.random() < 0.15:
            end_time = time.perf_counter()
            print(f"Gracz: {self.color} | Czas ruchu: {end_time - start_time:.4f} s | Odwiedzone węzły: {self.nodes_visited}")
            return random.choice(possible_moves)

        best_score = float('-inf')
        best_moves = []
        alpha = float('-inf')
        beta = float('inf')

        for r, c in possible_moves:
            snap = game.snapshot()

            game.grid[r][c]['owner'] = self.player_id
            game.check_for_cycles_around(r, c)

            score = self.minimax(
                game,
                self.depth - 1,
                alpha,
                beta,
                False
            )

            game.restore(snap)

            if score > best_score:
                best_score = score
                best_moves = [(r, c)]
            elif score == best_score:
                best_moves.append((r, c))
            
            if self.use_alpha_beta:
                alpha = max(alpha, score)

        end_time = time.perf_counter()
        print(f"Gracz: {self.color} | Czas ruchu: {end_time - start_time:.4f} s | Odwiedzone węzły: {self.nodes_visited}")
        return random.choice(best_moves) if best_moves else None

    def minimax(self, game, depth, alpha, beta, maximizing):
        self.nodes_visited += 1
        
        if depth == 0 or game.check_full():
            return self.evaluate_board(game)

        enemy_id = 3 - self.player_id

        if maximizing:
            max_eval = float('-inf')
            for r in range(LOGICAL_GRID_SIZE):
                for c in range(LOGICAL_GRID_SIZE):
                    if game.grid[r][c]['owner'] == 0 and not game.grid[r][c]['captured']:
                        snap = game.snapshot()
                        game.grid[r][c]['owner'] = self.player_id
                        game.check_for_cycles_around(r, c)

                        eval = self.minimax(game, depth - 1, alpha, beta, False)
                        
                        game.restore(snap)
                        max_eval = max(max_eval, eval)
                        
                        # --- WARUNEK ALFA-BETA ---
                        if self.use_alpha_beta:
                            alpha = max(alpha, eval)
                            if beta <= alpha:
                                return max_eval
                        # -------------------------
            return max_eval
        else:
            min_eval = float('inf')
            for r in range(LOGICAL_GRID_SIZE):
                for c in range(LOGICAL_GRID_SIZE):
                    if game.grid[r][c]['owner'] == 0 and not game.grid[r][c]['captured']:
                        snap = game.snapshot()
                        game.grid[r][c]['owner'] = enemy_id
                        game.check_for_cycles_around(r, c)

                        eval = self.minimax(game, depth - 1, alpha, beta, True)
                        
                        game.restore(snap)
                        min_eval = min(min_eval, eval)
                        
                        # --- WARUNEK ALFA-BETA ---
                        if self.use_alpha_beta:
                            beta = min(beta, eval)
                            if beta <= alpha:
                                return min_eval # Odcięcie gałęzi!
                        # -------------------------
            return min_eval

