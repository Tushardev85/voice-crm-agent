from pipecat.frames.frames import EndFrame, LLMMessagesFrame

async def switch_to_voicemail_response(task):
    print("[VOICEMAIL DETECTED] Switching to voicemail mode...")
    try:
        await task.queue_frames([
            LLMMessagesFrame([
                {
                    "role": "assistant",
                    "content": "Hi! Just leaving a quick message. Feel free to call back whenever convenient!"
                }
            ]),
            EndFrame()
        ])
        print("[VOICEMAIL MODE] Message sent and call ended.")
    except Exception as e:
        print("[ERROR] Failed to handle voicemail response:", e)

async def switch_to_human_conversation(task):
    print("[HUMAN DETECTED] Proceeding with normal interaction...")
    # You can optionally queue a message to start the convo
    await task.queue_frames([
        LLMMessagesFrame([
            {"role": "assistant", "content": "Please introduce yourself to the user."}
        ])
    ])

async def terminate_call(task):
    print("[CALL TERMINATION REQUESTED] Ending the call immediately.")
    await task.queue_frames([EndFrame()])