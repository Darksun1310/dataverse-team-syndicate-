import pandas as pd

# Load the datasets with correct paths
sku_master = pd.read_csv('sku_master.csv')
order_history = pd.read_csv('order_transactions.csv')
warehouse_constraints = pd.read_csv('warehouse_constraints.csv')

### OPTIMIZATION: FINAL SLOTTING PLAN

# 0. State Tracking: Bin Weights
# We must track the current weight of every bin to avoid overfilling
# Merge sku_master with constraints to get limits, but simpler:
# 1. Total current weight per bin
bin_weights = sku_master.groupby('current_slot')['weight_kg'].sum().to_dict()
# 2. Max weight per bin
bin_limits = warehouse_constraints.set_index('slot_id')['max_weight_kg'].to_dict()

with open('debug.log', 'w') as f:
    f.write(f"DEBUG: Unique SKU Temp Reqs: {sku_master['temp_req'].unique()}\n")
    f.write(f"DEBUG: Unique Bin Temp Zones: {warehouse_constraints['temp_zone'].unique()}\n")

# Helper to check occupancy and update
def can_fit(bin_id, added_weight):
    current_w = bin_weights.get(bin_id, 0.0)
    limit = bin_limits.get(bin_id, 999999.0) # Default to high if unknown, but should be known
    return (current_w + added_weight) <= limit

def update_bin_weight(bin_id, added_weight):
    bin_weights[bin_id] = bin_weights.get(bin_id, 0.0) + added_weight

# 1. Identify High-Velocity SKUs in Aisle B
aisle_b_bins = warehouse_constraints[warehouse_constraints['aisle_id'].str.startswith('B', na=False)]['slot_id'].unique()

# Calculate velocity
velocity_map = order_history.groupby('sku_id').size().reset_index(name='order_count')

# Current slots in Aisle B
current_slots = sku_master[['sku_id', 'current_slot']].copy()
aisle_b_skus = current_slots[current_slots['current_slot'].isin(aisle_b_bins)].copy()
aisle_b_skus = aisle_b_skus.merge(velocity_map, on='sku_id', how='left').fillna(0)
aisle_b_skus = aisle_b_skus.sort_values(by='order_count', ascending=False)

# 2. Find "Safe" Destination Bins (Aisle A or C etc, NOT B)
target_bins_df = warehouse_constraints[~warehouse_constraints['aisle_id'].str.startswith('B', na=False)]

def find_new_slot(sku_id, current_plan):
    sku_info = sku_master[sku_master['sku_id'] == sku_id].iloc[0]
    sku_temp = sku_info['temp_req']
    sku_weight = sku_info['weight_kg']
    
    # Filter bins by temperature
    eligible_bins = target_bins_df[target_bins_df['temp_zone'] == sku_temp]
    
    for _, bin_row in eligible_bins.iterrows():
        bin_id = bin_row['slot_id']
        
        # SKIP if bin is already a target for another move
        if bin_id in current_plan.values():
             continue

        if can_fit(bin_id, sku_weight):
            return bin_id
    return None

# 3. Generate the 50-Move Roadmap
moves = {}
MAX_MOVES = 50

# Priority 1: High-velocity items in Aisle B
with open('debug.log', 'a') as f:
    for sku in aisle_b_skus['sku_id']:
        if len(moves) >= MAX_MOVES:
            break
        
        new_bin = find_new_slot(sku, moves)
        if new_bin:
            moves[sku] = new_bin
            # Update weight immediately so next iteration sees it
            sku_val_row = sku_master[sku_master['sku_id'] == sku].iloc[0]
            sku_weight = sku_val_row['weight_kg']
            update_bin_weight(new_bin, sku_weight)
            
            if len(moves) <= 5:
                f.write(f"DEBUG MOVE: SKU={sku}, Temp={sku_val_row['temp_req']}, Weight={sku_weight}, NewBin={new_bin}, NewBinWeight={bin_weights[new_bin]}\n")

# Priority 2: Temperature violations
temp_merged = sku_master.merge(warehouse_constraints, left_on='current_slot', right_on='slot_id', how='left')
violations = temp_merged[temp_merged['temp_req'] != temp_merged['temp_zone']]


# Filter violations that are NOT already moved (e.g. if they were in Aisle B and moved, they are fixed)
# Using 'current_slot' implies original state.
# We check if sku is already in 'moves'.

for sku in violations['sku_id']:
    if len(moves) >= MAX_MOVES:
        break
    if sku not in moves:
        new_bin = find_new_slot(sku, moves)
        if new_bin:
            moves[sku] = new_bin
            sku_weight = sku_master[sku_master['sku_id'] == sku].iloc[0]['weight_kg']
            update_bin_weight(new_bin, sku_weight)

# 4. Create the final_slotting_plan.csv
final_plan_df = pd.DataFrame(list(moves.items()), columns=['SKU_ID', 'Bin_ID'])

# Fill remaining SKUs with their current (valid) locations
remaining_skus = current_slots[~current_slots['sku_id'].isin(final_plan_df['SKU_ID'])].rename(columns={'sku_id': 'SKU_ID', 'current_slot': 'Bin_ID'})
final_output = pd.concat([final_plan_df, remaining_skus])

final_output.to_csv('final_slotting_plan.csv', index=False)
print(f"Slotting Map generated with {len(moves)} optimized moves.")
