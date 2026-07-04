from src.core.interfaces import TtsProvider


async def _tokens(words):
    for w in words:
        yield w


async def _collect(async_iter):
    return [chunk async for chunk in async_iter]


async def test_sentence_chunk_preserves_all_text():
    words = ["Hi ", "there, ", "how ", "are ", "you", "?"]
    chunks = await _collect(TtsProvider.sentence_chunk(_tokens(words)))
    assert "".join(chunks).replace(" ", "") == "Hi there, how are you?".replace(" ", "")


async def test_sentence_chunk_never_yields_empty_stream_for_nonempty_input():
    chunks = await _collect(TtsProvider.sentence_chunk(_tokens(["hello "])))
    assert len(chunks) > 0


async def test_sentence_chunk_handles_empty_input():
    chunks = await _collect(TtsProvider.sentence_chunk(_tokens([])))
    assert chunks == []
