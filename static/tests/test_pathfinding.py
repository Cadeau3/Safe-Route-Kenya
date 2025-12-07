from app import find_safest_path

def test_straight_path():
    grid = [[0]*5 for _ in range(5)]
    path, cost = find_safest_path((0,0),(4,0),grid)
    assert path[0] == (0,0)
    assert path[-1] == (4,0)
    assert len(path) == 5

def test_blocked_cell_risk():
    grid = [[0]*5 for _ in range(5)]
    grid[0][2] = 999  # extremely risky cell
    path, cost = find_safest_path((0,0),(4,0),grid)
    assert (2,0) not in path
