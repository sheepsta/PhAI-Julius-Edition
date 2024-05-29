import heapq
import matplotlib.pyplot as plt
import numpy as np
import torch
from models import MLPModel
import random
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from a_star import a_star


class Node:
    def __init__(self, x, y, z, g=0, h=0, parent=None):
        self.x = x
        self.y = y
        self.z = z
        self.g = g  # Cost from start to current node
        self.h = h  # Heuristic cost from current node to end
        self.f = g + h  # Total cost
        self.parent = parent

    def __lt__(self, other):
        return self.f < other.f


def heuristic(a, b):
    return abs(a.x - b.x) + abs(a.y - b.y) + abs(a.z - b.z)


def a_star_search(occupancy_map, start, goal, model=None, device=None):
    start_node = Node(*start)
    goal_node = Node(*goal)
    open_list = []
    closed_list = set()
    heapq.heappush(open_list, start_node)
    g_score = {start: 0}
    came_from = {}
    expanded_states = []

    while open_list:
        current_node = heapq.heappop(open_list)
        expanded_states.append(
            (current_node.x, current_node.y, current_node.z))

        if (current_node.x, current_node.y, current_node.z) == (goal_node.x, goal_node.y, goal_node.z):
            return reconstruct_path(came_from, current_node), expanded_states

        closed_list.add((current_node.x, current_node.y, current_node.z))

        neighbors = get_neighbors(current_node, occupancy_map)
        for neighbor in neighbors:
            if (neighbor.x, neighbor.y, neighbor.z) in closed_list:
                continue

            tentative_g_score = g_score[(
                current_node.x, current_node.y, current_node.z)] + 1

            if (neighbor.x, neighbor.y, neighbor.z) not in g_score or tentative_g_score < g_score[(neighbor.x, neighbor.y, neighbor.z)]:
                came_from[(neighbor.x, neighbor.y, neighbor.z)] = current_node
                g_score[(neighbor.x, neighbor.y, neighbor.z)
                        ] = tentative_g_score
                h_value = heuristic(neighbor, goal_node)

                if model and device:
                    f_star_value = model_defined_f_star(
                        model, device, neighbor, start_node, goal_node, occupancy_map, tentative_g_score, h_value)
                    neighbor.f = f_star_value
                else:
                    neighbor.f = tentative_g_score + h_value

                if not any(node for node in open_list if node == neighbor and node.f <= neighbor.f):
                    heapq.heappush(open_list, neighbor)

    return None, expanded_states


def get_neighbors(node, occupancy_map):
    neighbors = []
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            for dz in [-1, 0, 1]:
                if dx == 0 and dy == 0 and dz == 0:
                    continue
                nx, ny, nz = node.x + dx, node.y + dy, node.z + dz
                if 0 <= nx < occupancy_map.shape[0] and 0 <= ny < occupancy_map.shape[1] and 0 <= nz < occupancy_map.shape[2] and occupancy_map[nx, ny, nz] == 0:
                    neighbors.append(Node(nx, ny, nz))
    return neighbors


def model_defined_f_star(model, device, coord, start, goal, occupancy_map, g_value, h_value):
    occupancy_tensor = torch.tensor(occupancy_map).float().unsqueeze(0)
    start_tensor = torch.zeros_like(occupancy_tensor)
    goal_tensor = torch.zeros_like(occupancy_tensor)
    coord_tensor = torch.zeros_like(occupancy_tensor)

    start_tensor[0, start.x, start.y, start.z] = 1
    goal_tensor[0, goal.x, goal.y, goal.z] = 1
    coord_tensor[0, coord.x, coord.y, coord.z] = 1

    input_tensor = torch.cat((occupancy_tensor, start_tensor,
                             goal_tensor, coord_tensor), dim=0).unsqueeze(0).to(device)
    input_tensor = input_tensor.float() / input_tensor.max()  # Normalize input
    g_h_values = torch.tensor(
        [g_value, h_value]).float().unsqueeze(0).to(device)

    with torch.no_grad():
        f_star_value = model(input_tensor, g_h_values).item()
    return f_star_value


def reconstruct_path(came_from, current_node):
    total_path = [(current_node.x, current_node.y, current_node.z)]
    while (current_node.x, current_node.y, current_node.z) in came_from:
        current_node = came_from[(
            current_node.x, current_node.y, current_node.z)]
        total_path.append((current_node.x, current_node.y, current_node.z))
    total_path.reverse()
    return total_path


def visualize_expanded_states(occupancy_map, model_expanded_states, regular_expanded_states):
    fig = plt.figure(figsize=(12, 6))

    # Model A* plot
    ax = fig.add_subplot(121, projection='3d')
    occupancy_map_np = occupancy_map.numpy()
    expanded_coords_model = np.array(list(model_expanded_states))

    ax.voxels(occupancy_map_np, edgecolor='k')
    ax.scatter(expanded_coords_model[:, 0], expanded_coords_model[:, 1],
               expanded_coords_model[:, 2], c='red', label='Expanded States')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title('Model A* Expanded States')
    ax.legend()

    # Regular A* plot
    ax = fig.add_subplot(122, projection='3d')
    expanded_coords_regular = np.array(list(regular_expanded_states))

    ax.voxels(occupancy_map_np, edgecolor='k')
    ax.scatter(expanded_coords_regular[:, 0], expanded_coords_regular[:, 1],
               expanded_coords_regular[:, 2], c='red', label='Expanded States')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title('Regular A* Expanded States')
    ax.legend()

    plt.tight_layout()
    plt.savefig('compare.png')


def find_unoccupied_coordinate(occupancy_map):
    size = occupancy_map.shape
    while True:
        x = random.randint(0, size[0] - 1)
        y = random.randint(0, size[1] - 1)
        z = random.randint(0, size[2] - 1)
        if occupancy_map[x, y, z] == 0:
            return (x, y, z)


def generate_start_and_goal(occupancy_map):
    start = find_unoccupied_coordinate(occupancy_map)
    goal = find_unoccupied_coordinate(occupancy_map)
    while goal == start:  # Ensure start and goal are not the same
        goal = find_unoccupied_coordinate(occupancy_map)
    return start, goal


def run_and_compare_searches(map_index, model, device):
    map_file = f'maps/map_{map_index}.pt'
    occupancy_map = torch.load(map_file).numpy()
    start, goal = generate_start_and_goal(occupancy_map=occupancy_map)
    print(f"Start: {start}, Goal: {goal}")

    # Run A* with model-defined f* values
    _, model_expanded_states = a_star_search(
        occupancy_map, start, goal, model, device)
    model_expanded_count = len(model_expanded_states)

    # Run regular A* search
    _, g_values, regular_expanded_states = a_star(occupancy_map, start, goal)
    regular_expanded_count = len(regular_expanded_states)

    # Print number of states expanded
    print(f'Model A* expanded {model_expanded_count} states')
    print(f'Regular A* expanded {regular_expanded_count} states')
    if (regular_expanded_count < model_expanded_count):
        # Visualize expanded states
        visualize_expanded_states(torch.tensor(
            occupancy_map), model_expanded_states, regular_expanded_states)


# Load the trained model
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
input_size = (20 * 20 * 20 * 4) + 2
output_size = 1
model = MLPModel(input_size=input_size, output_size=output_size).to(device)
model_path = 'model.pth'
model.load_state_dict(torch.load(model_path))
model.eval()

# Run and compare searches
run_and_compare_searches(map_index=0, model=model, device=device)