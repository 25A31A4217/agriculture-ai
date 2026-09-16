import pickle

# --------------------------------------------------
# SMART AGRICULTURE - CROP TRAINING DATA
# --------------------------------------------------
# Format:
# N, P, K, Temperature, Humidity, pH, Crop

data = [

    [90, 42, 43, 20, 80, 6.5, "Rice"],
    [85, 58, 41, 21, 82, 6.7, "Rice"],
    [80, 45, 42, 23, 75, 6.4, "Rice"],

    [60, 55, 44, 25, 65, 6.0, "Wheat"],
    [30, 30, 25, 18, 60, 6.2, "Wheat"],

    [70, 50, 40, 28, 70, 6.8, "Maize"],
    [50, 35, 30, 27, 68, 6.9, "Maize"],

    [40, 40, 35, 30, 55, 7.0, "Cotton"]

]

# Number of nearest examples
k = 3

model = {

    "data": data,

    "k": k

}

# Save model
with open("crop_model.pkl", "wb") as file:

    pickle.dump(model, file)

print()
print("======================================")
print("🌱 SMART AGRICULTURE MODEL")
print("======================================")
print("✅ Model created successfully!")
print("✅ crop_model.pkl saved!")
print("======================================")