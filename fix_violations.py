import pandas as pd

# Load your current plan and the master data
final_map = pd.read_csv('final_slotting_plan.csv')
constraints = pd.read_csv('warehouse_constraints.csv')
sku_info = pd.read_csv('sku_master.csv')

# Standardize columns for consistency with the provided logic
sku_info = sku_info.rename(columns={
    'sku_id': 'SKU_ID', 
    'temp_req': 'temp_zone', 
    'weight_kg': 'weight'
})
constraints = constraints.rename(columns={
    'slot_id': 'Bin_ID', 
    'max_weight_kg': 'weight_limit'
})

# 1. IDENTIFY THE VIOLATIONS
full_check = final_map.merge(sku_info[['SKU_ID', 'temp_zone', 'weight']], on='SKU_ID')
full_check = full_check.merge(constraints[['Bin_ID', 'temp_zone', 'weight_limit']], on='Bin_ID', suffixes=('_sku', '_bin'))

# Filter for temperature mismatches
violations = full_check[full_check['temp_zone_sku'] != full_check['temp_zone_bin']].copy()

print(f"DEBUG: Found {len(violations)} temperature violations.")

# 2. CREATE A POOL OF VALID EMPTY BINS
# Get all bins not currently in your plan to use as "safety" spots
used_bins = set(final_map['Bin_ID'])
available_bins = constraints[~constraints['Bin_ID'].isin(used_bins)].copy()

print(f"DEBUG: Found {len(available_bins)} available bins for swapping.")

def force_fix(row):
    # Find an available bin that matches the SKU temperature and weight limit
    match = available_bins[
        (available_bins['temp_zone'] == row['temp_zone_sku']) & 
        (available_bins['weight_limit'] >= row['weight'])
    ]
    
    if not match.empty:
        new_bin = match.iloc[0]['Bin_ID']
        # Remove this bin from the available pool so it's not double-booked
        available_bins.drop(match.index[0], inplace=True)
        return new_bin
    return row['Bin_ID'] # Fallback to old bin if no match

# Apply the fix to the violations
if not violations.empty:
    violations['Bin_ID'] = violations.apply(force_fix, axis=1)

# 3. REBUILD THE FINAL PLAN
# Remove the old incorrect rows and append the fixed ones
clean_plan = final_map[~final_map['SKU_ID'].isin(violations['SKU_ID'])]
fixed_plan = pd.concat([clean_plan, violations[['SKU_ID', 'Bin_ID']]])

# 4. FINAL WEIGHT CHECK FOR OVERLOADED BINS
# Calculate current weights
weight_check = fixed_plan.merge(sku_info[['SKU_ID', 'weight']], on='SKU_ID')
bin_weights = weight_check.groupby('Bin_ID')['weight'].sum().reset_index()
bin_weights = bin_weights.merge(constraints[['Bin_ID', 'weight_limit']], on='Bin_ID')

overloaded_bins = bin_weights[bin_weights['weight'] > bin_weights['weight_limit']]
print(f"DEBUG: {len(overloaded_bins)} Bins are overloaded. Attempting to fix...")

if not overloaded_bins.empty:
    for _, bin_row in overloaded_bins.iterrows():
        bin_id = bin_row['Bin_ID']
        excess_weight = bin_row['weight'] - bin_row['weight_limit']
        
        # Get SKUs in this bin
        skus_in_bin = weight_check[weight_check['Bin_ID'] == bin_id].sort_values(by='weight', ascending=False)
        
        # Move heaviest SKU that solves or helps the overload
        # We just take the heaviest one and move it.
        if not skus_in_bin.empty:
            sku_to_move = skus_in_bin.iloc[0]
            sku_id = sku_to_move['SKU_ID']
            sku_weight = sku_to_move['weight']
            # We need temp info for this SKU
            sku_temp = sku_info[sku_info['SKU_ID'] == sku_id].iloc[0]['temp_zone']
            
            # Find a new bin
            # Filter available bins (remember to update available_bins pool if using same logic, 
            # but used_bins is from START of script. Better to re-calculate used bins or just trust available_bins 
            # if we updated it correctly in force_fix.
            # actually force_fix updated `available_bins` in place drop. So it is current.)
            
            match = available_bins[
                (available_bins['temp_zone'] == sku_temp) & 
                (available_bins['weight_limit'] >= sku_weight)
            ]
            
            if not match.empty:
                new_bin = match.iloc[0]['Bin_ID']
                available_bins.drop(match.index[0], inplace=True)
                
                # Update the plan
                fixed_plan.loc[fixed_plan['SKU_ID'] == sku_id, 'Bin_ID'] = new_bin
                print(f"DEBUG: Moved {sku_id} from {bin_id} to {new_bin} to relieve overload.")


fixed_plan[['SKU_ID', 'Bin_ID']].to_csv('final_slotting_plan_FIXED.csv', index=False)
print(f"Fixed {len(violations)} temperature violations and attempted payload fixes. Saved to final_slotting_plan_FIXED.csv")
