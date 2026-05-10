"""
PaytarAI — Voice Transcription Endpoint

Whisper primary + AssemblyAI Medical Mode fallback ile ses transkripsiyon.
"""

from fastapi import APIRouter, UploadFile, File, Form

router = APIRouter(tags=["Voice"])


@router.post("/voice/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(...),
    user_role: str = Form("producer"),
):
    """
    Ses dosyasını metne çevirir.

    - Her iki rol için Whisper Large V3 primary
    - Veteriner rolünde: ilaç ismi eşleşmezse AssemblyAI fallback

    TODO (Faz 4): Whisper + AssemblyAI entegrasyonu
    """
    return {
        "transcript": "[Ses transkripsiyon Faz 4'te aktif olacak]",
        "source": "placeholder",
        "user_role": user_role,
    }
