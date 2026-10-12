"""Connected empty regions and Chinese area scoring (stones + territory)."""
def score_board(board, overrides=None, komi=7.5):
    n = len(board)
    overrides = overrides or {}
    seen = set()
    regions = []
    stones = {'B': 0, 'W': 0}
    territory = {'B': 0, 'W': 0, 'N': 0}
    for y in range(n):
        for x in range(n):
            value = board[y][x]
            if value:
                stones['B' if value == 1 else 'W'] += 1
                continue
            if (x, y) in seen: continue
            points, boundary, stack = [], set(), [(x, y)]
            seen.add((x, y))
            while stack:
                a, b = stack.pop()
                points.append([a, b])
                for c, d in ((a-1,b),(a+1,b),(a,b-1),(a,b+1)):
                    if not (0 <= c < n and 0 <= d < n): continue
                    neighbor = board[d][c]
                    if neighbor: boundary.add(neighbor)
                    elif (c,d) not in seen:
                        seen.add((c,d)); stack.append((c,d))
            owner = 'B' if boundary == {1} else 'W' if boundary == {2} else 'N'
            region_id = f'{x},{y}'
            owner = overrides.get(region_id, owner)
            if owner not in territory: raise ValueError('无效的空地归属')
            territory[owner] += len(points)
            regions.append(dict(id=region_id, points=points, owner=owner))
    black = stones['B'] + territory['B']
    white = stones['W'] + territory['W'] + komi
    delta = black - white
    return dict(regions=regions, stones=stones, territory=territory, komi=komi,
                black=black, white=white, winner='B' if delta > 0 else 'W' if delta < 0 else 'N', margin=abs(delta))
