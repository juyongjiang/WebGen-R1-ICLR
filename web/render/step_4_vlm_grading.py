import openai
import base64
import re
from openai import OpenAI
import time
import os


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

model_name = "gpt-4o-2024-11-20"
appearance_prompt = """
## Instruction:
You are tasked with evaluating the functional design of a webpage that had been constructed based on the following instruction:

{instruction}

Grade the webpage's appearance on a scale of 0 to 5 (5 being highest), considering the following criteria:

  - Successful Rendering: Does the webpage render correctly without visual errors? Are colors, fonts, and components displayed as specified?
  - Content Relevance: Does the design align with the website's purpose and user requirements? Are elements (e.g., search bars, report formats) logically placed and functional?
  - Layout Harmony: Is the arrangement of components (text, images, buttons) balanced, intuitive, and clutter-free?
  - Modernness & Beauty: Does the design follow contemporary trends (e.g., minimalism, responsive layouts)? Are colors, typography, and visual hierarchy aesthetically pleasing?

Grading Scale:

  - 0 (Unacceptable): The webpage fails to load (e.g., raises errors), is completely blank, or is entirely non-functional. There is no visible or assessable content, layout, or design.
  - 1 (Poor): Major rendering issues (e.g., broken layouts, incorrect colors). Content is irrelevant or missing. Layout is chaotic. Design is outdated or visually unappealing.
  - 2 (Below Average): Partial rendering with noticeable errors. Content is partially relevant but poorly organized. Layout lacks consistency. Design is basic or uninspired.
  - 3 (Average): Mostly rendered correctly with minor flaws. Content is relevant but lacks polish. Layout is functional but unremarkable. Design is clean but lacks modern flair.
  - 4 (Good): Rendered well with no major errors. Content is relevant and logically organized. Layout is harmonious and user-friendly. Design is modern and visually appealing.
  - 5 (Excellent): Flawless rendering. Content is highly relevant, intuitive, and tailored to user needs. Layout is polished, responsive, and innovative. Design is cutting-edge, beautiful, and memorable.

## Task:
Review the provided screenshot(s) of the webpage. Provide a detailed analysis and then assign a grade (0-5) based on your analysis. Highlight strengths, weaknesses, and how well the design adheres to the specifications.

## Your Response Format:

Analysis: [2-4 paragraphs addressing all criteria, referencing the instruction]

Grade: [0-5]

## Your Response:
"""

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

def get_score_result(image_paths, instruction):
    base64_images = []
    
    for image_path in image_paths:    
        base64_image = encode_image(image_path)
        base64_images.append(base64_image)
        
    prompt = appearance_prompt.format(
        instruction=instruction,
    )
    
    user_content = [
        {
            "type": "text",
            "text": prompt
        }
    ]
    
    for base64_image in base64_images:
        user_content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            }
        )

    retry_count = 0
    delay = 1
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            chat_response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": user_content}
                ]
            )
            return chat_response.choices[0].message.content
        except Exception as e:
            print(f"Request exception, retrying {retry_count + 1}/{max_retries}...")
            retry_count += 1
            time.sleep(delay)
            delay *= 2  
    return "Grade: 0"


def first_grade_int(text: str) -> int:
    """
    Return the first integer that appears *anywhere after* the substring
    'Grade' (case–insensitive).  
    If no such integer exists, return 0.

    Parameters
    ----------
    text : str
        The input string to scan.

    Returns
    -------
    int
        The first integer following the word 'Grade', or 0 if none found.
    """
    #  ▸ 'Grade'  (any capitalization)
    #  ▸ .*?       any characters (non‑greedy) including newlines
    #  ▸ (-?\d+)   capture an optional sign and at least one digit
    match = re.search(r'Grade.*?(\d)', text, flags=re.IGNORECASE | re.DOTALL)
    return int(match.group(1)) if match else 0.0
