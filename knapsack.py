import numpy as np
values = [1, 2, 5, 6] # value of each item
weights = [2, 3, 4, 5] # weight of each item

capacity = 8 # Maximum weight knapsack can hold

vLen = len(values)
wLen = len(weights)

if vLen != wLen:
    print("Every value must have a weight")
    exit()

n = wLen # Number of items to choose from


table = np.zeros((n + 1, capacity + 1), dtype=int)

for i in range(1, n + 1):
    for w in range (1, capacity + 1):
        if weights[i - 1] <= w:
            table[i][w] = max(values[i - 1] + table[i - 1][w - weights[i - 1]], table[i - 1][w])
        else:
            table[i][w] = table[i - 1][w]


selected = np.zeros(n, dtype=bool)
w = capacity

for i in range(n, 0, -1):
    if table[i][w] != table[i - 1][w]:
        selected[i - 1] = True
        w -= weights[i - 1]

max_value = table[n][capacity]
selected_mask = selected

print(f"Maximum value: {max_value}")
print(f"Selected items mask: {selected_mask}")
print(f"Selected items: {np.where(selected_mask)[0]}")
print(f"Selected weights: {[weights[i] for i in range(len(weights)) if selected_mask[i]]}")
print(f"Selected values: {[values[i] for i in range(len(values)) if selected_mask[i]]}")
