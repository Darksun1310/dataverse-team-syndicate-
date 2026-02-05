import pandas as pd
import numpy as np

# Load the datasets
# Updated filenames based on actual directory contents
sku_master = pd.read_csv('sku_master.csv')
order_history = pd.read_csv('order_transactions.csv') # Was order_history.csv
warehouse_constraints = pd.read_csv('warehouse_constraints.csv')
picker_movement = pd.read_csv('picker_movement.csv')

### 1. RESOLVING DECIMAL DRIFT (sku_master.csv)
# Logic: Identify weights that are ~10x the median of their product category.
def fix_decimal_drift(df):
    # Updated column name 'weight' -> 'weight_kg'
    # Calculate median weight per category to establish a baseline
    category_medians = df.groupby('category')['weight_kg'].transform('median')
    
    # Flag SKUs where weight is significantly higher (e.g., > 8x) than median
    drift_mask = df['weight_kg'] > (category_medians * 8)
    
    # Apply correction: divide by 10
    df.loc[drift_mask, 'weight_kg'] = df.loc[drift_mask, 'weight_kg'] / 10
    return df, drift_mask.sum()

sku_master, drift_count = fix_decimal_drift(sku_master)
sku_master.to_csv('sku_master.csv', index=False)
print(f"Fixed {drift_count} SKUs with Decimal Drift.")

### 2. IDENTIFYING GHOST INVENTORY
# Logic: Find SKUs assigned to bins not present in the official warehouse topology.
# Updated logic: Use sku_master['current_slot'] as source of truth for assignments
# Updated column name 'Bin_ID' -> 'slot_id'
valid_bins = warehouse_constraints['slot_id'].unique()

# Check sku_master for invalid slots
ghost_skus = sku_master[~sku_master['current_slot'].isin(valid_bins)]
ghost_sku_list = ghost_skus['sku_id'].unique()

print(f"Detected {len(ghost_sku_list)} SKUs in Ghost Bins. These must be re-slotted.")

### 3. THE SHORTCUT PARADOX (picker_movement.csv)
# Logic: Prove Picker 07 is skipping safety zones by checking velocity.
def detect_shortcuts(df, picker_id='PICKER-07'): # Updated ID format to match CSV (PICKER-XX)
    # Ensure picker_id matches format (script used 'Picker 07', CSV uses 'PICKER-07')
    # If the user input generic 'picker_id', we assume they mean the string literal unless we adjust.
    # The original script hardcoded default 'Picker 07', but CSV has 'PICKER-07'. I will align this.
    
    picker_df = df[df['picker_id'] == picker_id].sort_values(by=['movement_timestamp'])
    
    # Calculate velocity
    # We have 'travel_distance_m' directly.
    # Time difference between movements
    picker_df['time_diff'] = pd.to_datetime(picker_df['movement_timestamp']).diff().dt.total_seconds()
    
    # Velocity = Distance / Time
    # Handle potential divide by zero or NaNs
    picker_df['velocity'] = picker_df['travel_distance_m'] / picker_df['time_diff']
    
    # If velocity exceeds physical limits (e.g., 5m/s), they skipped a barrier
    shortcuts = picker_df[picker_df['velocity'] > 5.0] 
    return shortcuts

# Check for PICKER-07 instead of "Picker 07"
illegal_moves = detect_shortcuts(picker_movement, picker_id='PICKER-07')
illegal_moves.to_csv('forensic_evidence_picker07.csv', index=False)
print(f"Evidence Found: {len(illegal_moves)} instances of Picker 07 skipping safety zones.")
print("Exported forensic evidence to forensic_evidence_picker07.csv")

### 4. BOTTLENECK ANALYSIS: AISLE B PEAK
# Logic: Filter for 19:00 peak hours to find high-collision alerts.
# Need to derive 'aisle' merging with sku_master or parsing.
# Using merge with sku_master on sku_id to get 'current_slot' -> 'aisle'
merged_movement = picker_movement.merge(sku_master[['sku_id', 'current_slot']], on='sku_id', how='left')
merged_movement['aisle'] = merged_movement['current_slot'].str.split('-').str[0]

merged_movement['hour'] = pd.to_datetime(merged_movement['movement_timestamp']).dt.hour

# Original logic looked for aisle 'B'. Valid aisles look like 'A01', 'B01'. 
# Assuming 'Aisle B' refers to all 'B' aisles (B01-BXX).
peak_aisle_b = merged_movement[(merged_movement['hour'] == 19) & (merged_movement['aisle'].fillna('').str.startswith('B'))]

# Group by minute to see if more than 2 pickers are present
minute_density = peak_aisle_b.groupby(pd.to_datetime(peak_aisle_b['movement_timestamp']).dt.minute)['picker_id'].nunique()
collisions = minute_density[minute_density > 2]
print(f"Collision Alerts: {len(collisions)} minutes with high picker density in Aisle B.")

