import re

def _mod_sort_key(name):
    m = re.search(r'\d+', name)
    return int(m.group()) if m else 9999

# Test cases
test_titles = [
    "Module 1 Notes",
    "Module 10 Notes",
    "Module 2 Notes",
    "Welcome Material",
    "Module 3 Lab",
    "Final Project",
    "Module 11 Advanced"
]

# Expected order:
# 1. Module 1 Notes
# 2. Module 2 Notes
# 3. Module 3 Lab
# 4. Module 10 Notes
# 5. Module 11 Advanced
# 6. Welcome Material (9999)
# 7. Final Project (9999) - Note: current logic sorts by title after order if order is same, but _mod_sort_key only looks at numbers.

sorted_titles = sorted(test_titles, key=_mod_sort_key)

print("Original order:")
print(test_titles)
print("\nSorted order (Natural):")
for title in sorted_titles:
    print(f"- {title}")

# Verify specific transitions
assert sorted_titles.index("Module 1 Notes") < sorted_titles.index("Module 2 Notes")
assert sorted_titles.index("Module 2 Notes") < sorted_titles.index("Module 10 Notes")
assert sorted_titles.index("Module 10 Notes") < sorted_titles.index("Module 11 Advanced")

print("\nVerification Successful!")
