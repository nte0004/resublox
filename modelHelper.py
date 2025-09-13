#!/usr/bin/env python3

from sentence_transformers import SentenceTransformer
import os

# ranker.py is configured for any of these.
MODEL_NAME = 'all-MiniLM-L6-v2'
#MODEL_NAME = 'all-MiniLM-L12-v2'
#MODEL_NAME = 'all-mpnet-base-v2'

DOWNLOAD_DIR = './models'

def download_model():
    """Download and save a sentence transformer model to specified directory."""
    
    # Create directory if it doesn't exist
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # Full path for the model
    model_path = os.path.join(DOWNLOAD_DIR, MODEL_NAME.replace('/', '_'))
    
    print(f"Downloading model: {MODEL_NAME}")
    print(f"Saving to: {model_path}")
    
    try:
        # Download the model (this will cache it first)
        model = SentenceTransformer(MODEL_NAME)
        
        # Save to our specified directory
        model.save(model_path)
        
        print(f"✅ Model successfully downloaded and saved to: {model_path}")
        print(f"Model size on disk: {get_folder_size(model_path):.2f} MB")
        
        # Test loading from local path
        print("\n🧪 Testing local load...")
        test_model = SentenceTransformer(model_path)
        test_embedding = test_model.encode(["Test sentence"])
        print(f"✅ Successfully loaded from local directory!")
        print(f"Embedding shape: {test_embedding.shape}")
        
    except Exception as e:
        print(f"❌ Error downloading model: {str(e)}")
        return False
    
    return True

def get_folder_size(folder_path):
    """Calculate folder size in MB."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total_size += os.path.getsize(filepath)
    return total_size / (1024 * 1024)  # Convert to MB

if __name__ == "__main__":
    success = download_model()
    
    if success:
        print(f"\n📁 To use this model later:")
        model_path = os.path.join(DOWNLOAD_DIR, MODEL_NAME.replace('/', '_'))
        print(f"model = SentenceTransformer('{model_path}')")
    else:
        print("\n❌ Download failed!")
