import asyncio
import audioop
import base64
import json
import os
import io
from urllib.parse import parse_qs
import openai
import websockets
from fastapi import WebSocket, Request, APIRouter, Depends
from pydub import AudioSegment
from starlette.responses import Response
from sqlmodel import Session, select
from ..utils.db import engine
from ..models.voice_model import Voice
from ..utils.helpers import get_current_user
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect
from pydub.exceptions import CouldntDecodeError
import src.utils.audioop_compat as audioop_compat
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
from amazon_transcribe.exceptions import BadRequestException
from ..constants.agent_constants import (
    NAME_OF_AGENT,
    COMPANY_NAME,
    GREETING_MESSAGE,
    SPECIAL_INSTRUCTIONS,
    TARGET_FIRST_NAME,
    ROLE_OF_BOT,
    SAMPLE_QUESTIONS
)
from ..constants.common import (
    OPENAI_API_KEY,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    ELEVENLABS_API_KEY,
    SERVER_ADDRESS,
    REGION
)
from ..utils.helpers import get_voice_id
from ..signals.campaign_signals import dequeue_contact
# END IMPORTS

# GLOBAL VARIABLES
ELEVENLABS_VOICE_ID = ""
STREAM_SID = ""
USER_ID = ""

# SDKs Initialization
openai.api_key = OPENAI_API_KEY
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ROUTER INITIATION
voice_router = APIRouter()


# MAKE CALL API


@voice_router.post('/make-call/{phone_number}', tags=['make call'])
async def create_call(request: Request, phone_number: str, current_user_id: str = Depends(get_current_user)):
    global USER_ID, ELEVENLABS_VOICE_ID, NAME_OF_AGENT, GREETING_MESSAGE, ROLE_OF_BOT, COMPANY_NAME, TARGET_FIRST_NAME
    USER_ID = current_user_id
    data = await request.json() 
    NAME_OF_AGENT = data['agent_name']
    GREETING_MESSAGE = data['greeting']
    ROLE_OF_BOT = data['role']
    COMPANY_NAME = data['industry']
    TARGET_FIRST_NAME = data['receiver_name']
    ELEVENLABS_VOICE_ID = get_voice_id(current_user_id)
    call = twilio_client.calls.create(
        url=f'{SERVER_ADDRESS}/call/',
        to=f'+{phone_number}',
        from_=os.environ['TWILIO_PHONE_NUMBER']
    )
    return Response(content=json.dumps({'detail': 'Calling..'}), media_type='text/xml')


# CALL WEBHOOK


@voice_router.post('/call/', tags=['call webhook'])
async def handle_call(request: Request):
    response = VoiceResponse()
    data = await request.body()
    data = data.decode('utf-8')
    form_data = parse_qs(data)
    call_sid = form_data.get('CallSid')[0]
    connect = Connect()
    connect.stream(
        url=f'wss://{request.headers.get("host")}/stream/{call_sid}')
    response.append(connect)
    response.say('Call ended.')
    return Response(content=str(response), media_type='text/xml')

# WEBSOCKET ENDPOINT


@voice_router.websocket('/stream/{call_sid}')
async def websocket_endpoint(websocket: WebSocket, call_sid):
    await websocket.accept()
    await wait_for_user_input(websocket)

conversation_history = []

# HANDLE AWS TRANSCRIBE STREAM CLASS


class TranscriptEventHandler(TranscriptResultStreamHandler):
    def __init__(self, out_stream, websocket):
        super().__init__(out_stream)
        self.websocket = websocket

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        global conversation_history, NAME_OF_AGENT, GREETING_MESSAGE, ROLE_OF_BOT, COMPANY_NAME, TARGET_FIRST_NAME
        results = transcript_event.transcript.results
        final_results = ""
        for result in results:
            if result.is_partial:
                print("Partial result:", result.alternatives[0].transcript)
            else:
                prompt = f"""As {NAME_OF_AGENT}, an {ROLE_OF_BOT} specialist, your primary goal is to engage 
                the customer positively and proactively to secure a deal or schedule a meeting. Always be ready to 
                ask relevant follow-up questions to delve deeper into the customer's e-commerce needs and concerns. 
                When a customer's inquiry aligns with predefined {SAMPLE_QUESTIONS}, tailor your response to fit 
                those scenarios accurately, with a particular focus on e-commerce solutions. Adherence to the 
                following {SPECIAL_INSTRUCTIONS} is crucial for maintaining the desired interaction quality and 
                company standards. At the beginning of each conversation, especially upon receiving a greeting 
                from the customer, introduce yourself as {NAME_OF_AGENT} from {COMPANY_NAME} with a warm and brief 
                overview of how {COMPANY_NAME} assists e-commerce business owners in leveraging missed and after-hours 
                calls to their advantage. This introduction should be engaging and prompt a natural continuation of the 
                conversation, setting a positive tone for the interaction.
                You must greet with the following greeting message and introduce the user about {COMPANY_NAME} and yourself:
                {GREETING_MESSAGE}.
                Do not tell user about the assistancy. Remember you have called the user. And the caller does
                not ask about like "how can I assist you?". So keep it real.
                Do not say sentences like "How can I assist you?" in conversation.
                The user name is {TARGET_FIRST_NAME}.
                """
                if len(conversation_history) == 0:
                    conversation_history.append(
                        {'role': 'system', 'content': prompt})
                print("Final result:", result.alternatives[0].transcript)
                final_results = result.alternatives[0].transcript
                if final_results.lower() not in ['hm', 'uh', 'oh,', 'uh,', 'hm,', 'mhm', 'mhm,']:
                    try:  # adding try because when user ends call the app might get crash due to TypeError
                        conversation_history.append(
                            {'role': 'user', 'content': final_results})
                        await chat_completion(conversation_history, self.websocket, STREAM_SID)
                    except TypeError:
                        pass

# TRANSCRIBE VOICE AWS TRANSCRIBE


async def wait_for_user_input(websocket):

    transcribe_client = TranscribeStreamingClient(region=REGION)
    stream = await transcribe_client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=16000,
        media_encoding="pcm",
    )

    async def write_chunks():
        global STREAM_SID
        while True:
            json_data = await websocket.receive_text()
            data = json.loads(json_data)
            if data['event'] == 'start':
                print('Streaming is starting')
            elif data['event'] == 'stop':
                print('\nStreaming has stopped')
                await stream.input_stream.end_stream()
                websocket.close()
                has_data_in_queue = await dequeue_contact(USER_ID)
            elif data['event'] == 'media':
                STREAM_SID = data['streamSid']
                audio = base64.b64decode(data['media']['payload'])
                # Decode mu-law to linear PCM
                audio = audioop_compat.ulaw2lin(audio, 2)
                audio = audioop.ratecv(audio, 2, 1, 8000, 16000, None)[0]
                await stream.input_stream.send_audio_event(audio_chunk=audio)

    handler = TranscriptEventHandler(stream.output_stream, websocket)
    try:
        await asyncio.gather(write_chunks(), handler.handle_events())
    except BadRequestException as e:
        print(f"Error: {e}")
    finally:
        await stream.input_stream.end_stream()
        has_data_in_queue = await dequeue_contact(USER_ID)


# SPLIT TEXT FOR ELEVENS LAB
async def text_chunker(chunks):
    """Split text into chunks, ensuring to not break sentences."""
    splitters = ('.', ',', '?', '!', ';', ':', '—',
                 '-', '(', ')', '[', ']', '}', ' ')
    buffer = ''

    async for text in chunks:
        if buffer.endswith(splitters):
            yield buffer + ' '
            buffer = text
        elif text.startswith(splitters):
            yield buffer + text[0] + ' '
            buffer = text[1:]
        else:
            buffer += text

    if buffer:
        yield buffer + ' '


# CONVERT ELEVENSLAB AUDIO INTO TELEPHONIC FORMAT & SEND TO TWILIO SOCKET
async def stream(audio_stream, twilio_ws, stream_sid):
    async for chunk in audio_stream:
        if chunk:
            try:
                audio = AudioSegment.from_file(
                    io.BytesIO(chunk), format='mp3')
                if audio.channels == 2:
                    audio = audio.set_channels(1)
                resampled = audioop.ratecv(
                    audio.raw_data, 2, 1, audio.frame_rate, 8000, None)[0]
                audio_segment = AudioSegment(
                    data=resampled, sample_width=audio.sample_width, frame_rate=8000, channels=1)
                pcm_audio = audio_segment.export(format='wav')
                pcm_data = pcm_audio.read()
                ulaw_data = audioop.lin2ulaw(pcm_data, audio.sample_width)
                message = json.dumps({'event': 'media', 'streamSid': stream_sid,
                                      'media': {'payload': base64.b64encode(ulaw_data).decode('utf-8'), }})

                try:
                    await twilio_ws.send_text(message)
                    print("Voice sent to user..")
                except websockets.exceptions.ConnectionClosedError:
                    twilio_ws.close()
                    has_data_in_queue = await dequeue_contact(USER_ID)
            except (CouldntDecodeError, IndexError):
                pass


# CONVERT TEXT INTO SPEECH USING ELEVENSLAB
async def text_to_speech_input_streaming(voice_id, text_iterator, twilio_ws, stream_sid):
    uri = f'wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id=eleven_monolingual_v1&optimize_streaming_latency=4'
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({'text': ' ', 'voice_settings': {'stability': 1, 'similarity_boost': True},
                                         'xi_api_key': ELEVENLABS_API_KEY, }))

        async def listen():
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    if data.get('audio'):
                        yield base64.b64decode(data['audio'])
                    elif data.get('isFinal'):
                        break
                except (websockets.exceptions.ConnectionClosed, websockets.exceptions.ConnectionClosedError):
                    twilio_ws.close()
                    has_data_in_queue = await dequeue_contact(USER_ID)
                    print('Connection closed')
                    break

        listen_task = asyncio.create_task(
            stream(listen(), twilio_ws, stream_sid))
        async for text in text_chunker(text_iterator):
            await websocket.send(json.dumps({'text': text, 'try_trigger_generation': True}))
        await websocket.send(json.dumps({'text': ''}))
        await listen_task


# GENERATE ANSWER VIA GPT
        #  ft:gpt-3.5-turbo-0613:personal:sara-call:8hkW2lVL
        # ft:gpt-3.5-turbo-0613:personal:textbackjack:8mS23Jbs
        # ft:gpt-3.5-turbo-0613:personal:callback-bot:8kzq5Cfm
async def chat_completion(messages, twilio_ws, stream_sid):
    global conversation_history
    response = await openai.ChatCompletion.acreate(model='ft:gpt-3.5-turbo-0613:personal:textbackjack:8mS23Jbs', messages=messages, temperature=0.5, stream=True,
                                                   max_tokens=250)

    async def text_iterator():
        full_resp = []
        async for chunk in response:
            delta = chunk['choices'][0]['delta']
            if 'content' in delta:
                content = delta['content']
                print(content, end=' ', flush=True)
                full_resp.append(content)
                yield content
            else:
                print('<end of gpt response>')
                break
        conversation_history.append(
            {'role': 'assistant', 'content': ' '.join(full_resp), })
    await text_to_speech_input_streaming(ELEVENLABS_VOICE_ID, text_iterator(), twilio_ws, stream_sid)
