import asyncio
import sys
import uuid

# Backend path setup
sys.path.append('.')

from services.analysis_service import AnalysisService
from models.video import Video
from schemas.api_models import ChartData

async def dummy_test():
    # Initialize service directly, ignoring repos since we only test a pure function
    service = AnalysisService(video_repository=None, result_repository=None)
    
    # Create dummy video
    dummy_video = Video(
        id=uuid.uuid4(),
        duration_seconds=5.0,
        original_filename="dummy_test.mp4"
    )
    
    # Generate chart data
    print("Generating Chart Data (Dataset/Labels format)...")
    chart_data_dict = service._generate_chart_data(dummy_video, visual_base=0.4, audio_base=0.6)
    
    print("\nRaw Output Dictionary:")
    print(chart_data_dict)
    
    # Validate against Pydantic schema
    try:
        validated_data = ChartData(**chart_data_dict)
        print("\n[SUCCESS] Pydantic Schema Validation Passed!")
        print(f"Labels count: {len(validated_data.labels)}")
        print(f"Datasets count: {len(validated_data.datasets)}")
        for idx, ds in enumerate(validated_data.datasets):
            print(f"  Dataset {idx + 1}: '{ds.label}' with {len(ds.data)} points")
    except Exception as e:
        print("\n[FAILED] Pydantic Schema Validation Error:")
        print(e)

if __name__ == "__main__":
    asyncio.run(dummy_test())
