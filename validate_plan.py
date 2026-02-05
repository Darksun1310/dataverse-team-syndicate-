import pandas as pd

# Load your generated map and the master constraints
final_map = pd.read_csv('final_slotting_plan_FIXED.csv')
constraints = pd.read_csv('warehouse_constraints.csv')
sku_info = pd.read_csv('sku_master.csv') 

# --- PRE-PROCESSING FOR VALIDATION ---
# Normalize column names to match the expected validation logic
# sku_info: sku_id -> SKU_ID, weight_kg -> weight, temp_req -> temp_zone
sku_info_clean = sku_info.rename(columns={
    'sku_id': 'SKU_ID', 
    'weight_kg': 'weight', 
    'temp_req': 'temp_zone'
})

# constraints: slot_id -> Bin_ID, max_weight_kg -> weight_limit
constraints_clean = constraints.rename(columns={
    'slot_id': 'Bin_ID',
    'max_weight_kg': 'weight_limit'
})

# -------------------------------------

def validate_submission(plan, master_constraints, skus):
    errors = []
    
    # 1. Check Format (Requirement: Exactly two columns: SKU_ID and Bin_ID)
    required_cols = ['SKU_ID', 'Bin_ID']
    # Sorting to ensure order doesn't fail the check if just swapped
    if sorted(list(plan.columns)) != sorted(required_cols):
        errors.append(f"Invalid Columns: Expected {required_cols}, got {list(plan.columns)}")
    
    # 2. Check for Temperature Violations (Automatic 0 Points)
    full_check = plan.merge(skus[['SKU_ID', 'temp_zone']], on='SKU_ID', how='left')
    full_check = full_check.merge(master_constraints[['Bin_ID', 'temp_zone']], on='Bin_ID', suffixes=('_sku', '_bin'), how='left')
    
    # Check for NaN violations (missing SKU or Bin info)
    if full_check['temp_zone_sku'].isnull().any():
        errors.append(f"WARNING: some SKUs in plan not found in master data.")
    if full_check['temp_zone_bin'].isnull().any():
        errors.append(f"WARNING: some Bins in plan not found in constraints.")

    violations = full_check[full_check['temp_zone_sku'] != full_check['temp_zone_bin']]
    # Filter out where data might be missing to avoid false positives on NaNs here (handled above)
    violations = violations.dropna(subset=['temp_zone_sku', 'temp_zone_bin'])
    
    if not violations.empty:
        errors.append(f"CRITICAL: {len(violations)} Temperature Violations detected!")
    
    # 3. Check for Weight Capacity
    # Calculate total weight per bin in your new plan
    weight_check = plan.merge(skus[['SKU_ID', 'weight']], on='SKU_ID', how='left')
    bin_weights = weight_check.groupby('Bin_ID')['weight'].sum().reset_index()
    bin_weights = bin_weights.merge(master_constraints[['Bin_ID', 'weight_limit']], on='Bin_ID', how='left')
    
    overloaded = bin_weights[bin_weights['weight'] > bin_weights['weight_limit']]
    if not overloaded.empty:
        errors.append(f"CRITICAL: {len(overloaded)} Bins are overloaded!")

    # 4. Check for Ghost Bins (Physical Truth)
    valid_bins = set(master_constraints['Bin_ID'])
    plan_bins = set(plan['Bin_ID'])
    invalid_bins = plan_bins - valid_bins
    if invalid_bins:
        errors.append(f"CRITICAL: {len(invalid_bins)} Bins do not exist in the warehouse topology!")

    return errors

# Run the check
validation_errors = validate_submission(final_map, constraints_clean, sku_info_clean)

if not validation_errors:
    print("✅ SUCCESS: Your Slotting Map is compliant with all Hard Constraints.")
else:
    print("❌ ERRORS FOUND:")
    for err in validation_errors:
        print(f" - {err}")
