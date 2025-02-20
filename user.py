import streamlit as st
import fitz  # PyMuPDF for handling PDFs
from PIL import Image
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
import json 
import re


# -----------------------------------------------------
# 1. Configure Streamlit Page and Hide Default Menu
# -----------------------------------------------------
st.set_page_config(
    page_title="Chatbot",
    layout="wide",
    initial_sidebar_state="expanded"
)

hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# -----------------------------------------------------
# 2. Load Environment Variables and Initialize ChatGroq
# -----------------------------------------------------
load_dotenv()
chatbot = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.2-11b-vision-preview"
    # model_name="llama-3.2-11b-vision-preview"
)

# -----------------------------------------------------
# 3. Caching Functions
# -----------------------------------------------------
# Use st.cache_resource for loading non-pickleable objects like PDF files.
def load_pdf(pdf_file: str):
    return fitz.open(pdf_file)

# Use st.cache_data with a custom hash function to ignore the pdf argument for caching.
def get_page_image(pdf, page_number: int):
    page = pdf.load_page(page_number)
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img


def get_page_text(pdf, page_number: int) -> str:
    page = pdf.load_page(page_number)
    return page.get_text()


def get_full_text(pdf) -> str:
    text_data = []
    for page_num in range(len(pdf)):
            text_data.append(pdf.load_page(page_num).get_text())
    return text_data


# -----------------------------------------------------
# 4. Helper Function for Chat Interaction
# -----------------------------------------------------
def ask_chatbot(prompt: str) -> str:
    response = chatbot.invoke(prompt)
    return response.content


# -----------------------------------------------------
# 5. Load PDF and Initialize Session State
# -----------------------------------------------------
pdf_file = "chapter1.pdf"
pdf = load_pdf(pdf_file)

if "page_number" not in st.session_state:
    st.session_state.page_number = 0


# -----------------------------------------------------
# 6. Main UI Layout
# -----------------------------------------------------
st.title("Chatbot with LLM")
st.markdown("---")


# Navigation row for Previous/Next buttons and page info.
nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1], gap="medium")
with nav_col1:
    # Previous Button
    prev_btn = st.button("Previous", key="prev_btn", use_container_width=True)
    if prev_btn:
        # if st.session_state.page_number > 0:
            st.session_state.page_number -= 1

with nav_col3:
    # Next Button
    next_btn = st.button("Next", key="next_btn", use_container_width=True)
    if next_btn:
        if st.session_state.page_number < len(pdf) - 1:
            st.session_state.page_number += 1

with nav_col2:
# Display Current Page Number
        st.write(f"**Page {st.session_state.page_number } - {st.session_state.page_number +1 } of {len(pdf)}**")               
        
st.subheader("PDF Viewer")

# Create two columns to display two pages
col_left, col_right = st.columns(2)

with col_left:
    # Display the left (current) page image
    current_page_img = get_page_image(pdf, st.session_state.page_number)
    st.image(current_page_img, use_container_width=True)

with col_right:
    # Check if a next page exists; if so, display it
    if st.session_state.page_number + 1 < len(pdf):
        next_page_img = get_page_image(pdf, st.session_state.page_number + 1)
        st.image(next_page_img, use_container_width=True)
  

st.subheader("Search for a Word in the Document")
search_query = st.text_input("Enter a word to search:")

text_data =  get_full_text(pdf)

if search_query:
    search_results = [(i + 1, text) for i, text in enumerate(text_data) if search_query.lower() in text.lower()]

    if search_results:
        st.success(f"✅ Found {len(search_results)} results!")

        for page_num, text in search_results[:5]:  # Show first 5 results
            with st.expander(f"📄 Page {page_num} (Click to Expand)"):
                # Highlight matches
                highlighted_text = re.sub(
                    rf"({re.escape(search_query)})",
                    r'<span style="background-color: yellow; font-weight: bold;">\1</span>',
                    text,
                    flags=re.IGNORECASE
                )
                st.markdown(highlighted_text, unsafe_allow_html=True)

    else:
        st.warning("⚠️ No matches found!")      


st.subheader("Ask about the Current Page")
# Extract text from the current page.
current_page_text = get_page_text(pdf, st.session_state.page_number)
user_input = st.text_input("Enter your question:")

# If user input is provided, generate an answer
if user_input:
    with st.spinner("Thinking..."):
        prompt = (
            f"Give me an answer based on this data:\n"
            f"{current_page_text}\n\n"
            f"No preamble. Here is the question:\n"
            f"{user_input}"
        )
        answer = ask_chatbot(prompt)

    # Display the answer in an expandable container
    with st.expander("View Answer", expanded=True):
        st.markdown(answer, unsafe_allow_html=True)    



# ---------- Page Summary Section ----------
st.subheader("Page Summary")

# Button to generate the summary
if st.button("Generate Summary", type="primary"):
    with st.spinner("Summarizing..."):
        prompt = (
            f"Summarize the following content:\n"
            f"{current_page_text}\n\n"
            f"No preamble."
        )
        summary = ask_chatbot(prompt)

    # Display a confirmation message
    st.info("✅ Summary Generated Successfully!")

    # Display the summary in an expandable container
    with st.expander("View Summary", expanded=True):
        st.markdown(summary, unsafe_allow_html=True)


current_page_text = get_page_text(pdf, st.session_state.page_number)
# Button to generate questions and answers
if st.button("Generate Questions and Answers", type="primary"):
    with st.spinner("Generating..."):
        prompt = (
                f"Generate multiple-choice questions (MCQs) and answers based on the following content:\n"
                f"{current_page_text}\n\n"
                f"The output must be in JSON format as a Python list of dictionaries, following this structure:\n"
                f"""[
                    {{
                        "question": "What is the main topic of the passage?",
                        "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
                        "answer": "B) Option 2"
                    }},
                    {{
                        "question": "Which statement is correct?",
                        "options": ["A) Statement 1", "B) Statement 2", "C) Statement 3", "D) Statement 4"],
                        "answer": "C) Statement 3"
                    }},
                    ...
                ]

                Guidelines:
                - Provide exactly **four** answer choices per question.
                - Ensure **one correct answer** per question, which must match one of the options.
                - Do **not** include extra text like "Here is the JSON output."
                - Do **not** wrap the response inside code blocks (`json`, `python`, etc.).
                - Ensure all answer choices appear in the "options" list.
                - Do **not** provide explanations—only the JSON response.
                """
            )



        # Get response from chatbot
        Questions_Answers = ask_chatbot(prompt)  

        # Debugging: Print the response before processing
        # st.write("Raw response from chatbot:", Questions_Answers)

        # Check if the response is empty or None
        if not Questions_Answers:
            st.error("Chatbot returned an empty response. Please try again.")
        else:
            try:
                # If the response is a string, try parsing it
                if isinstance(Questions_Answers, str):
                    Questions_Answers = json.loads(Questions_Answers)
                
                # Ensure it's a list of dictionaries
                if not isinstance(Questions_Answers, list) or not all(isinstance(q, dict) for q in Questions_Answers):
                    st.error("Invalid response format from chatbot.")
                else:
                    st.title("MCQ Questions")

                    # Custom CSS & JS to prevent DevTools, Right Click, Copy-Paste, and Screenshots
                    secure_code = """
                        <style>
                            /* Disable text selection */
                            body {
                                -webkit-user-select: none;
                                -moz-user-select: none;
                                -ms-user-select: none;
                                user-select: none;
                            }
                            /* Disable right-click */
                            # body {
                            #     pointer-events: none;
                            # }
                            /* Disable inspecting images */
                            img {
                                pointer-events: none;
                            }
                        </style>

                        <script>
                            // Disable right-click
                            document.addEventListener("contextmenu", function(event) {
                                event.preventDefault();
                            });

                            // Disable certain key combinations
                            document.addEventListener("keydown", function(event) {
                                if (
                                    event.key === "F12" || 
                                    event.key === "F11" || 
                                    (event.ctrlKey && (event.key === "u" || event.key === "c" || event.key === "x" || event.key === "s")) ||
                                    (event.ctrlKey && event.shiftKey && (event.key === "I" || event.key === "J"))
                                ) {
                                    event.preventDefault();
                                }
                            });

                            // Detect DevTools open
                            setInterval(function() {
                                let widthThreshold = window.outerWidth - window.innerWidth > 160;
                                let heightThreshold = window.outerHeight - window.innerHeight > 160;
                                if (widthThreshold || heightThreshold) {
                                    document.body.innerHTML = "";
                                    alert("DevTools detected! Closing the page for security.");
                                    window.close();
                                }
                            }, 1000);
                        </script>
                    """

                    # Inject security features into Streamlit
                    st.markdown(secure_code, unsafe_allow_html=True)


                    for idx, q in enumerate(Questions_Answers):
                        # Find the correct answer's index in options
                        correct_index = q["options"].index(q["answer"])

                        # Show question with default correct answer pre-selected
                        st.subheader(f"Q{idx+1}: {q['question']}")
                        user_answer = st.radio(
                            "Select your answer:",
                            q["options"],
                            index=correct_index,  # ✅ Default selection to correct answer
                            key=f"q{idx}"
                        )

                        # Check and display feedback
                        if user_answer == q["answer"]:
                            st.success(f"✅ Correct! Answer: {q['answer']}")
                        else:
                            st.error(f"❌ Incorrect. Correct Answer: {q['answer']}")

                    st.write("---")
                    st.write("✅ **End of Quiz** ✅")

            except json.JSONDecodeError as e:
                st.error(f"JSON decoding error: {e}")



            



