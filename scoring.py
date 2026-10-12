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

def stone_groups(board):
    n, seen, groups = len(board), set(), []
    for y in range(n):
        for x in range(n):
            if not board[y][x] or (x,y) in seen: continue
            color = board[y][x]
            seen.add((x,y)); stack = [(x,y)]; points = []
            while stack:
                a,b = stack.pop(); points.append([a,b])
                for c,d in ((a-1,b),(a+1,b),(a,b-1),(a,b+1)):
                    if 0<=c<n and 0<=d<n and board[d][c]==color and (c,d) not in seen:
                        seen.add((c,d)); stack.append((c,d))
            groups.append(dict(id=f'stone-{x},{y}', points=points, color='B' if color==1 else 'W'))
    return groups

def settle_board(board, group_owners=None, empty_overrides=None):
    effective = [row[:] for row in board]
    groups = stone_groups(board)
    dead = {'B':0, 'W':0}
    for group in groups:
        group['owner'] = (group_owners or {}).get(group['id'], group['color'])
        if group['owner'] not in ('B','W'): raise ValueError('棋子归属必须为黑方或白方。')
        group['dead'] = group['owner'] != group['color']
        if group['dead']:
            dead[group['color']] += len(group['points'])
            for x,y in group['points']: effective[y][x] = 0
    result = score_board(effective, empty_overrides)
    result.update(groups=groups, dead=dead)
    return result
