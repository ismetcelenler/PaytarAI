"""
PaytarAI — Voice Transcription Endpoint

Whisper Large V3 ile ses transkripsiyonu.
Transkript dogrudan chat input'a duser, kullanici gondermeden once duzenleyebilir.
AssemblyAI fallback kaldirildi (ADR-007).
"""

from fastapi import APIRouter, UploadFile, File

router = APIRouter(tags=["Voice"])


@router.post("/voice/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(...),
):
    """
    Ses dosyasini Whisper Large V3 ile metne cevirir.

    Transkript frontend'de chat input alanina yazilir.
    Kullanici metni gorup duzenledikten sonra gondermeden once kontrol edebilir.

    TODO (Faz 4): Whisper API entegrasyonu
    """
    # Placeholder — Faz 4'te gercek Whisper API cagirisi eklenecek
    return {
        "transcript": "[Whisper transkripsiyonu Faz 4'te aktif olacak]",
        "source": "whisper",
    }
