from ultralytics import YOLO
import cv2
from collections import Counter

# Load YOLO model
model = YOLO("yolov8n.pt")

# Price list
PRICE_LIST = {
    "bottle": 3.0,
    "cup": 5.0,
    "cell phone": 2000.0,
    "laptop": 3500.0,
    "person": 0.0
}

# Open webcam
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

while True:

    ret, frame = cap.read()

    if not ret:
        print("Cannot access camera")
        break

    # Run YOLO detection
    results = model(frame)

    # Draw detection boxes
    annotated_frame = results[0].plot()

    # Store detected objects
    detected_objects = []

    # Loop through detections
    for box in results[0].boxes:

        cls_id = int(box.cls[0])

        class_name = model.names[cls_id]

        detected_objects.append(class_name)

    # Count detected objects
    object_counts = Counter(detected_objects)

    # Calculate total price
    total_price = 0

    for obj, count in object_counts.items():

        if obj in PRICE_LIST:

            total_price += PRICE_LIST[obj] * count

    # Display counts
    y_position = 30

    for obj, count in object_counts.items():

        # Get item price
        item_price = PRICE_LIST.get(obj, 0)

        # Calculate subtotal
        subtotal = item_price * count

        text = f"{obj}: {count} = RM{subtotal:.2f}"

        cv2.putText(
            annotated_frame,
            text,
            (10, y_position),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        y_position += 35

    # Display total price
    total_text = f"TOTAL = RM{total_price:.2f}"

    cv2.putText(
        annotated_frame,
        total_text,
        (10, y_position + 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 0, 255),
        3
    )

    # Print to terminal
    print("Detected:", object_counts)
    print("Total Price: RM", total_price)

    # Show output
    cv2.imshow("YOLO Smart Checkout", annotated_frame)

    # Press Q to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
git --version
cap.release()
cv2.destroyAllWindows()