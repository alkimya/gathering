Code Examples
=============

This section provides practical examples of using GatheRing.

Customer Service Bot
--------------------

.. code-block:: python

   from gathering.core import BasicAgent

   # Create a customer service agent
   support_agent = BasicAgent.from_config({
       "name": "SupportBot",
       "age": None,  # Ageless AI
       "history": "Specialized customer service AI with extensive training "
                  "in conflict resolution and product knowledge",
       "llm_provider": "openai",
       "model": "gpt-4",
       "personality_blocks": ["empathetic", "patient", "helpful", "professional"],
       "competencies": ["customer_service", "problem_solving", "product_knowledge"],
       "tools": ["filesystem"]  # For accessing knowledge base
   })

   # Handle customer inquiry
   response = support_agent.process_message(
       "I ordered a product 2 weeks ago and haven't received it yet. "
       "I'm very frustrated!"
   )
   print(response)
   # Output: "I completely understand your frustration, and I sincerely 
   #          apologize for the delay. Let me help you track your order..."

Research Assistant Team
-----------------------

.. code-block:: python

   from gathering.core import BasicAgent, BasicConversation

   # Create a research team
   data_analyst = BasicAgent.from_config({
       "name": "Dr. Data",
       "age": 35,
       "history": "PhD in Statistics, 10 years analyzing research data",
       "llm_provider": "openai",
       "personality_blocks": ["analytical", "precise", "thorough"],
       "tools": ["calculator"]
   })

   literature_expert = BasicAgent.from_config({
       "name": "Prof. Scholar",
       "age": 50,
       "history": "Professor of Literature Review, published 100+ papers",
       "llm_provider": "anthropic",
       "personality_blocks": ["knowledgeable", "methodical", "critical"]
   })

   writer = BasicAgent.from_config({
       "name": "Dr. Writer",
       "age": 40,
       "history": "Science writer, expert in making complex topics accessible",
       "llm_provider": "openai",
       "personality_blocks": ["creative", "clear", "engaging"],
       "tools": ["filesystem"]
   })

   # Create research collaboration
   research_team = BasicConversation.create([data_analyst, literature_expert, writer])

   # Start research discussion
   research_team.add_message(
       data_analyst,
       "I've found interesting patterns in climate data showing a 15% increase. "
       "We need to contextualize this."
   )

   # Get responses from team
   responses = research_team.process_turn()
   for response in responses:
       print(f"\n{response['agent'].name}:")
       print(response['content'])

Educational Tutor
-----------------

.. code-block:: python

   from gathering.core import BasicAgent

   # Create a math tutor
   math_tutor = BasicAgent.from_config({
       "name": "Prof. Math",
       "age": 45,
       "history": "Mathematics professor with 20 years teaching experience, "
                  "specialized in making math fun and accessible",
       "llm_provider": "openai",
       "model": "gpt-4",
       "personality_blocks": ["patient", "encouraging", "clear", "enthusiastic"],
       "competencies": ["mathematics", "teaching", "curriculum_design"],
       "tools": ["calculator"]
   })

   # Adaptive teaching based on student level
   def teach_concept(tutor, student_level, topic):
       prompt = f"I'm a {student_level} student. Can you explain {topic}?"
       return tutor.process_message(prompt)

   # Elementary level
   response = teach_concept(math_tutor, "5th grade", "fractions")
   print("Elementary explanation:", response)

   # High school level  
   response = teach_concept(math_tutor, "high school", "derivatives")
   print("\nHigh school explanation:", response)

   # University level
   response = teach_concept(math_tutor, "university", "Fourier transforms")
   print("\nUniversity explanation:", response)

Creative Writing Assistant
--------------------------

.. code-block:: python

   from gathering.core import BasicAgent

   # Create a creative writing assistant
   writing_assistant = BasicAgent.from_config({
       "name": "Wordsmith",
       "history": "Award-winning author and creative writing instructor",
       "llm_provider": "anthropic",
       "model": "claude-3",
       "personality_blocks": ["creative", "imaginative", "supportive", "insightful"],
       "competencies": ["creative_writing", "storytelling", "editing"],
       "tools": ["filesystem"]  # For saving drafts
   })

   # Story development session
   story_seed = "A detective who can only solve crimes while sleepwalking"

   # Generate story elements
   response = writing_assistant.process_message(
       f"I have this story idea: '{story_seed}'. "
       "Can you help me develop the main character?"
   )
   print("Character Development:", response)

   # Continue with plot
   response = writing_assistant.process_message(
       "That's great! Now what would be an interesting first case?"
   )
   print("\nFirst Case:", response)

Technical Documentation Bot
---------------------------

.. code-block:: python

   from gathering.core import BasicAgent

   # Create a technical writer
   tech_writer = BasicAgent.from_config({
       "name": "DocBot",
       "history": "Senior technical writer with expertise in API documentation "
                  "and developer guides",
       "llm_provider": "openai",
       "personality_blocks": ["precise", "clear", "structured", "thorough"],
       "competencies": ["technical_writing", "api_documentation", "markdown"],
       "tools": ["filesystem"]
   })

   # Generate API documentation
   api_info = """
   Function: getUserData
   Parameters: userId (string), includeMetadata (boolean)
   Returns: User object with name, email, created_at
   Errors: 404 if user not found, 401 if unauthorized
   """

   response = tech_writer.process_message(
       f"Please create proper API documentation for this: {api_info}"
   )
   print(response)

Medical Consultation Assistant
------------------------------

.. note::
   This is for educational purposes only. Not for actual medical advice.

.. code-block:: python

   from gathering.core import BasicAgent

   # Create a medical information assistant
   medical_assistant = BasicAgent.from_config({
       "name": "Dr. Info",
       "age": 40,
       "history": "Medical information specialist, NOT for diagnosis - "
                  "provides educational health information only",
       "llm_provider": "anthropic",
       "personality_blocks": ["empathetic", "careful", "informative", "responsible"],
       "competencies": ["health_education", "medical_terminology", "communication"]
   })

   # Provide health information
   response = medical_assistant.process_message(
       "What are common symptoms of dehydration?"
   )
   print(response)
   # Always includes disclaimer about seeking real medical advice

Code Review Assistant
---------------------

.. code-block:: python

   from gathering.core import BasicAgent

   # Create a code reviewer
   code_reviewer = BasicAgent.from_config({
       "name": "ReviewBot",
       "history": "Senior software engineer specializing in code quality, "
                  "security, and best practices",
       "llm_provider": "openai",
       "personality_blocks": ["analytical", "constructive", "thorough", "helpful"],
       "competencies": ["code_review", "security", "performance", "best_practices"],
       "tools": ["filesystem"]  # For analyzing code files
   })

   # Review code
   code_snippet = '''
   def calculate_total(items):
       total = 0
       for i in range(len(items)):
           total = total + items[i].price * items[i].quantity
       return total
   '''

   response = code_reviewer.process_message(
       f"Please review this Python code:\n{code_snippet}"
   )
   print(response)
   # Provides suggestions about using enumerate, sum(), or list comprehension

Language Learning Partner
-------------------------

.. code-block:: python

   from gathering.core import BasicAgent, BasicConversation

   # Create language learning partners
   spanish_teacher = BasicAgent.from_config({
       "name": "María",
       "age": 30,
       "history": "Native Spanish speaker, certified language instructor",
       "llm_provider": "openai",
       "personality_blocks": ["patient", "encouraging", "cultural", "interactive"],
       "competencies": ["spanish", "language_teaching", "cultural_knowledge"]
   })

   student = BasicAgent.from_config({
       "name": "Learning Student",
       "age": 25,
       "history": "Beginner Spanish learner, eager to practice",
       "llm_provider": "anthropic",
       "personality_blocks": ["curious", "motivated", "mistake-prone"],
       "competencies": ["learning"]
   })

   # Create practice session
   practice = BasicConversation.create([spanish_teacher, student])
   
   # Start conversation
   practice.add_message(student, "¿Cómo se dice 'I am hungry' en español?")
   
   responses = practice.process_turn()
   print(f"{responses[0]['agent'].name}: {responses[0]['content']}")
   # María: "Se dice 'Tengo hambre'. Literally, it means 'I have hunger'..."
