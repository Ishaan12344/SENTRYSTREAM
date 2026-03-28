# SentryStream - AI-Powered Safety Violation Detection System

SentryStream is an intelligent video surveillance system that uses computer vision to detect workplace safety violations in real-time. The system monitors video feeds, identifies safety equipment compliance (hardhats, safety vests), and automatically reports violations to a cloud-based backend.

## 🏗️ System Architecture

```
┌─────────────────┐    HTTP POST     ┌─────────────────┐    PostgreSQL     ┌─────────────────┐
│   Video Stream  │ ──────────────► │   FastAPI        │ ───────────────► │   Supabase DB   │
│   (Detection)   │                 │   Backend        │                  │   (Database)    │
└─────────────────┘                 └─────────────────┘                  └─────────────────┘
         │                                   │                                       │
         │                                   │                                       │
         ▼                                   ▼                                       ▼
┌─────────────────┐    File Upload    ┌─────────────────┐    JSON/CSV       ┌─────────────────┐
│   Local Logs    │ ◄──────────────── │   Supabase       │ ◄──────────────── │   Local Files   │
│   (JSON/CSV)    │                   │   Storage        │                  │   (Images)      │
└─────────────────┘                   └─────────────────┘                  └─────────────────┘
```

## 📥 Input

### Video Input
- **Source**: IP Camera or Webcam
- **Format**: RTSP stream or USB camera
- **Resolution**: Variable (optimized for real-time processing)

### Detection Classes
The YOLOv8 model detects the following objects:
- **ALLOWED_CLASSES**: `{"Hardhat", "NO-Hardhat", "Safety Vest", "NO-Safety Vest", "Person"}`
- **VIOLATION_CLASSES**: `{"NO-Hardhat", "NO-Safety Vest"}`
- **SAFE_CLASSES**: `{"Hardhat", "Safety Vest"}`

### Configuration Parameters
- **Confidence Threshold**: 0.45 (minimum detection confidence)
- **Violation Cooldown**: 7 seconds (prevent duplicate reports)
- **Block Time**: 300 seconds (ignore same person violations)
- **Frame Skip**: 2 frames (performance optimization)

## 🔄 Data Flow

### 1. Video Processing Pipeline

```
Video Frame → YOLO Detection → Object Tracking → Violation Logic → Report Generation → Backend Transmission
```

**Detailed Steps:**
1. **Frame Capture**: Read frames from camera source
2. **Object Detection**: YOLOv8 model identifies objects with confidence scores
3. **Tracking**: Maintain object identities across frames using tracking IDs
4. **Violation Check**: Compare detected objects against violation classes
5. **Deduplication**: Prevent duplicate violations from same person within time window
6. **Report Creation**: Generate structured violation report with metadata

### 2. Violation Report Structure

```json
{
  "timestamp": "2026-03-28 21:31:15",
  "camera": "rtsp://192.168.29.100:8080/video",
  "violations": ["NO-Hardhat (ID 1)", "NO-Safety Vest (ID 2)"],
  "detections": [
    {
      "label": "NO-Hardhat",
      "confidence": 0.87,
      "bbox": [150, 200, 280, 350],
      "track_id": 1,
      "violation": true
    },
    {
      "label": "Person",
      "confidence": 0.92,
      "bbox": [140, 190, 290, 360],
      "track_id": 1,
      "violation": false
    }
  ],
  "image": "/path/to/violation_image.jpg"
}
```

### 3. Backend Processing

```
HTTP POST → Image Upload → Database Storage → Response
```

**API Endpoint**: `POST /report`
- **Content-Type**: `multipart/form-data`
- **Fields**:
  - `image`: Violation snapshot (File)
  - `data`: Violation report (JSON string)

## 📤 Output

### Real-time Display
- **Annotated Video**: Live video feed with bounding boxes
- **Color Coding**:
  - 🟢 Green: Safe objects (Hardhat, Safety Vest)
  - 🔴 Red: Violations (NO-Hardhat, NO-Safety Vest)
  - 🔵 Blue: Persons

### Console Output
```
🚨 VIOLATION: ['NO-Hardhat (ID 1)']
Saved: output/images/violation_20260328_213115.jpg
📡 Sent: 200
```

### API Response
```json
{"status": "saved"}
```

## 💾 Data Storage

### Supabase Database (PostgreSQL)

#### `violations` Table
```sql
CREATE TABLE violations (
    id SERIAL PRIMARY KEY,
    timestamp VARCHAR,
    camera VARCHAR,
    image_path VARCHAR,  -- Supabase Storage URL
    violations JSON      -- Array of violation strings
);
```

#### `detections` Table
```sql
CREATE TABLE detections (
    id SERIAL PRIMARY KEY,
    violation_id INTEGER REFERENCES violations(id),
    label VARCHAR,
    confidence FLOAT,
    bbox JSON,           -- [x1, y1, x2, y2]
    track_id INTEGER,
    violation INTEGER    -- Boolean as integer
);
```

### Supabase Storage
- **Bucket**: `violations`
- **Files**: JPEG images with UUID filenames
- **Access**: Public URLs for web viewing

### Local Storage (Fallback)
```
output/
├── images/           # Violation snapshots
├── violations/       # JSON reports
└── logs/            # CSV and JSON logs
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Supabase account and project
- IP Camera or Webcam

### Installation

1. **Clone and setup**:
```bash
git clone <repository>
cd SentryStream
pip install -r requirements.txt
```

2. **Configure Supabase**:
```bash
# Set your Supabase credentials in .env
SUPABASE_ANON_KEY=your_supabase_anon_key_here
```

3. **Database Setup**:
- Run `supabase_tables.sql` in Supabase SQL Editor
- Create storage bucket named `violations`

4. **Start Backend**:
```bash
cd backend
uvicorn app.main:app --reload
```

5. **Configure Detection**:
- Update `BACKEND_URL` in `backend/video_stream/detection.py`
- Set camera source in config

6. **Run Detection**:
```bash
python backend/video_stream/detection.py
```

## 🔧 Configuration

### Environment Variables
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?ssl=require
```

### Detection Parameters
- Edit `backend/video_stream/config.py` for class definitions
- Modify thresholds in `detection.py`

## 📊 Monitoring & Logs

### Real-time Monitoring
- Console output shows violations as they occur
- Annotated video display with live bounding boxes

### Log Files
- **events.csv**: Timestamped violation events
- **violations_log.json**: Complete violation reports
- **Images**: JPEG snapshots of violations

### API Endpoints
- `GET /`: Health check
- `GET /violations`: List all violations
- `GET /violations/{id}`: Detailed violation with detections

## 🛠️ Troubleshooting

### Common Issues

1. **"Invalid API key"**: Check Supabase credentials in `.env`
2. **"Table doesn't exist"**: Run the SQL schema in Supabase
3. **"Bucket not found"**: Create `violations` bucket in Supabase Storage
4. **Camera connection failed**: Check IP camera URL or webcam index

### Performance Tuning
- Adjust `SKIP_FRAMES` for frame rate vs CPU usage
- Modify `CONFIDENCE_THRESHOLD` for detection sensitivity
- Increase `VIOLATION_COOLDOWN_SEC` to reduce false positives

## 📈 System Metrics

- **Real-time Processing**: 15-30 FPS (depending on hardware)
- **Detection Accuracy**: Configurable confidence threshold
- **Storage**: Images in Supabase, metadata in PostgreSQL
- **Scalability**: Horizontal scaling with multiple camera feeds

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.