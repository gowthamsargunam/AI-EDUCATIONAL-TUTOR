import os
import streamlit as st
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from pytube import Search

# Initialize the Azure client
def initialize_client():
    endpoint = "https://models.github.ai/inference"
    token = os.environ["OPEN_API_KEY"]
    return ChatCompletionsClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(token),
    )

# Find relevant YouTube video
def find_youtube_video(topic, subject, level):
    try:
        query = f"{topic} {subject} {level} level tutorial"
        search_results = Search(query).results
        if search_results:
            return f"https://www.youtube.com/watch?v={search_results[0].video_id}"
        return None
    except Exception as e:
        st.error(f"Couldn't fetch YouTube video: {str(e)}")
        return None
    

def generate_educational_response(client, subject, topic, level, query):
    system_prompt = f"""
    You are an AI-powered educational tutor specializing in {subject}. 
    The student is learning about {topic} at a {level} level.
    Provide clear, step-by-step explanations tailored to the student's level.
    Break down complex concepts, use analogies when helpful, and provide examples.
    If the student asks a question, answer it thoroughly while teaching the underlying concepts.
    """
    
    try:
        response = client.complete(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            model="openai/gpt-4.1",
            temperature=0.7,
            top_p=0.9
        )
        # Get YouTube video
        video_url = find_youtube_video(topic, subject, level)
        lesson_content = response.choices[0].message.content
        
        if video_url:
            # Adding YouTube embed at the end of the lesson
            video_id = video_url.split('v=')[1]
            embed_html = f"""
            <div style="margin-top: 20px;">
                <h3>📺 Recommended Video Tutorial</h3>
                <iframe width="560" height="315" 
                    src="https://www.youtube.com/embed/{video_id}" 
                    frameborder="0" 
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                    allowfullscreen>
                </iframe>
                <p><a href="{video_url}" target="_blank">Watch on YouTube</a></p>
            </div>
            """
            lesson_content += embed_html
        else:
            lesson_content += "\n\n*Could not find a relevant YouTube video for this topic*"
            
        return lesson_content
    except Exception as e:
        return f"Error generating response: {str(e)}"

# Generate quiz questions with answers
def generate_quiz_with_answers(client, subject, topic, level, num_questions=10):
    prompt = f"""
    Generate {num_questions} {level}-level multiple choice quiz questions about {topic} in {subject}.
    For each question:
    1. Provide the question stem
    2. Provide 4 options labeled A) to D)
    3. Indicate the correct answer with "Correct Answer: X)"
    4. Include a brief explanation
    Format each question like this:
    
    Question 1: [question text]
    A) [option 1]
    B) [option 2]
    C) [option 3]
    D) [option 4]
    Correct Answer: [letter]
    Explanation: [brief explanation]
    """
    
    try:
        response = client.complete(
            messages=[
                {"role": "user", "content": prompt}
            ],
            model="openai/gpt-4.1",
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating quiz: {str(e)}"

# Clear chat history
def clear_content(content_type):
    if content_type == "lesson":
        st.session_state.messages = [
            msg for msg in st.session_state.messages 
            if not (msg["role"] == "assistant" and "lesson plan" in msg["content"].lower())
        ]
    elif content_type == "quiz":
        st.session_state.messages = [
            msg for msg in st.session_state.messages 
            if not (msg["role"] == "assistant" and "question 1:" in msg["content"].lower())
        ]
        if 'quiz_answers' in st.session_state:
            del st.session_state['quiz_answers']
        if 'user_answers' in st.session_state:
            del st.session_state['user_answers']
        if 'score' in st.session_state:
            del st.session_state['score']

# Parse quiz questions and answers
def parse_quiz(quiz_text):
    questions = []
    current_question = {}
    lines = quiz_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith('Question'):
            if current_question:
                questions.append(current_question)
            current_question = {
                'question': line.split(': ')[1],
                'options': [],
                'correct': '',
                'explanation': ''
            }
        elif line.startswith(('A)', 'B)', 'C)', 'D)')):
            current_question['options'].append(line[3:])
        elif line.startswith('Correct Answer:'):
            current_question['correct'] = line.split(': ')[1].strip(')')
        elif line.startswith('Explanation:'):
            current_question['explanation'] = line.split(': ')[1]
    
    if current_question:
        questions.append(current_question)
    
    return questions

def main():
    st.set_page_config(page_title="AI-Powered Educational Tutor", page_icon="🎓", layout="wide")
    
    # Initialize session states
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "quiz_questions" not in st.session_state:
        st.session_state.quiz_questions = []
    if "user_answers" not in st.session_state:
        st.session_state.user_answers = {}
    if "show_answers" not in st.session_state:
        st.session_state.show_answers = False
    
    # Sidebar for settings
    with st.sidebar:
        st.header("Settings")
        subject = st.selectbox(
            "Select Subject",
            ["Mathematics", "Science", "History", "Literature", "Computer Science", "Other"]
        )
        
        topic = st.text_input("Enter Topic (e.g., Algebra, World War II, Python Programming)")
        
        level = st.selectbox(
            "Select Difficulty Level",
            ["Beginner", "Intermediate", "Advanced"]
        )
        
        if st.button("New Lesson Plan"):
            with st.spinner("Creating a customized lesson plan..."):
                clear_content("lesson")
                client = initialize_client()
                lesson_plan = generate_educational_response(
                    client, 
                    subject, 
                    topic, 
                    level, 
                    f"Create a comprehensive lesson plan about {topic} for a {level} level student."
                )
                st.session_state.messages.append({"role": "assistant", "content": lesson_plan})
                st.rerun()
        
        if st.button("Practice a Quiz"):
            with st.spinner("Generating practice quiz..."):
                clear_content("quiz")
                client = initialize_client()
                quiz = generate_quiz_with_answers(client, subject, topic, level, 10)
                st.session_state.quiz_questions = parse_quiz(quiz)
                st.session_state.messages.append({"role": "assistant", "content": "Quiz generated! Scroll down to take the practice quiz."})
                st.rerun()
        
        if st.button("➕ Clear All", help="Reset the entire interface"):
            st.session_state.messages = []
            st.session_state.quiz_questions = []
            st.session_state.user_answers = {}
            st.session_state.show_answers = False
            st.rerun()

    # Main chat interface
    st.title(f"AI {subject} Tutor")
    st.caption(f"Teaching {topic} at {level} level")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)
    
    # Chat input
    if prompt := st.chat_input("Ask your question or request help"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                client = initialize_client()
                response = generate_educational_response(
                    client, subject, topic, level, prompt
                )
                st.markdown(response, unsafe_allow_html=True)
        
        st.session_state.messages.append({"role": "assistant", "content": response})

# Quiz section
    if st.session_state.quiz_questions:
        st.divider()
        st.header("Practice Quiz")
        
        if not st.session_state.show_answers:
            for i, question in enumerate(st.session_state.quiz_questions):
                st.subheader(f"{i+1}. {question['question']}")
                options = question['options']
                
                # Store user answers
                key = f"q_{i}"
                if key not in st.session_state.user_answers:
                    st.session_state.user_answers[key] = None
                
                cols = st.columns(4)
                for j, option in enumerate(options):
                    with cols[j % 4]:
                        if st.button(
                            f"{chr(65+j)}) {option}",
                            key=f"option_{i}_{j}",
                            on_click=lambda i=i, j=j: st.session_state.user_answers.update({f"q_{i}": chr(65+j)})
                        ):
                            pass
        
            if st.button("Submit Quiz", type="primary"):
                st.session_state.show_answers = True
                st.session_state.score = 0
                
                for i, question in enumerate(st.session_state.quiz_questions):
                    user_answer = st.session_state.user_answers.get(f"q_{i}")
                    if user_answer == question['correct']:
                        st.session_state.score += 1
                
                st.rerun()
        else:
            st.subheader(f"Your Score: {st.session_state.score}/10")
            if st.session_state.score < 7:
                st.warning("You might want to practice more!")
                if st.button("Practice Again"):
                    st.session_state.show_answers = False
                    st.session_state.user_answers = {}
                    st.rerun()
            else:
                st.success("Great job! You're doing well!")
            
            for i, question in enumerate(st.session_state.quiz_questions):
                user_answer = st.session_state.user_answers.get(f"q_{i}")
                is_correct = user_answer == question['correct']
                
                st.subheader(f"Question {i+1}: {question['question']}")
                for j, option in enumerate(question['options']):
                    prefix = ""
                    if chr(65+j) == user_answer:
                        prefix = "❌ Your answer: " if not is_correct else "✅ Your answer: "
                    elif chr(65+j) == question['correct']:
                        prefix = "✅ Correct answer: "
                    
                    st.text(f"{prefix}{chr(65+j)}) {option}")
                
                st.caption(f"Explanation: {question['explanation']}")
                st.divider()

if __name__ == "__main__":
    main()