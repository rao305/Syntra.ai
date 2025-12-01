# Gemini-Style UI Implementation Guide

This document provides a complete implementation guide for the Gemini-style UI, including both visual design (CSS/HTML) and behavioral characteristics (system prompts).

## 🎨 Visual Design Implementation

### Color Palette

| Element | Color Name | Hex Code | Description |
| :--- | :--- | :--- | :--- |
| **Main Background** | Dark Surface | `#131314` | The overall background of the page/chat area |
| **User Input Area** | Input Surface | `#202124` | The darker background of the input box and response bubbles |
| **Text Color** | High-Emphasis Text | `#e8eaed` | The default color for all text |
| **Response Block** | Background Accent | `#202124` | Response bubbles use the same subtle dark background |
| **Code Block** | Code Background | `#2f3032` | Slightly different shade for code blocks |
| **Placeholder Text** | Muted Gray | `#9aa0a6` | Placeholder text color |
| **Icon Color** | Gemini Blue | `#8ab4f8` | Color for the response icon (✨) |

### CSS Implementation

The Gemini-style CSS has been implemented in:
- `frontend/app/globals.css` - Global styles and Gemini-specific classes
- `frontend/components/message-bubble.tsx` - Message bubble styling
- `frontend/components/message-composer.tsx` - Input field styling
- `frontend/components/code-block.tsx` - Code block styling

#### Key CSS Classes

```css
/* Chat Content Wrapper - Fixed max-width for readability */
.chat-content-wrapper {
  max-width: 80ch;
  width: 100%;
  margin-left: auto;
  margin-right: auto;
  padding: 0 16px;
}

/* AI Response Container with Icon */
.ai-response-container {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

/* Gemini-style icon */
.ai-response-icon {
  font-size: 24px;
  color: #8ab4f8;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  margin-top: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* AI Response Bubble */
.ai-response-bubble {
  background-color: #202124;
  padding: 18px 20px;
  border-radius: 18px;
  margin-bottom: 24px;
  box-shadow: none;
  flex-grow: 1;
}

/* Code Block Styling */
.code-block-gemini {
  background-color: #2f3032;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
}
```

### Font Styling

- **Body Text**: Roboto (16px base size)
- **Headings & Prompts**: Google Sans (medium weight 500)
- **Line Height**: 1.6 for readability in response bubbles

Fonts are loaded from Google Fonts CDN in `frontend/app/layout.tsx`.

### Expanding Text Input

The input field automatically expands as the user types:
- **Min Height**: 32px
- **Max Height**: 200px
- **Auto-resize**: Based on content scrollHeight
- **Container**: `bg-[#202124]` with `rounded-[28px]`

## 🧠 Behavioral Implementation

### System Prompt

The Gemini-style behavioral characteristics are implemented in the system prompt located at:
- `backend/app/services/dac_persona.py` - `DAC_SYSTEM_PROMPT`

### Core Behavioral Characteristics

#### 1. **Contextual Awareness**
- Maintains awareness of the entire conversation history
- Provides context-specific follow-up answers
- Never asks the user to repeat information
- Resolves pronouns and vague references using conversation history

#### 2. **Direct & Analytical Tone**
- Professional, analytical, and helpful
- Avoids excessive emotional language, emojis, or sycophantic praise
- Focuses on providing comprehensive information rather than flattery
- Default tone: Direct, analytical, and professional

#### 3. **Information-Driven**
- Prioritizes accuracy and clarity
- Generates detailed, well-structured, and comprehensive answers
- Grounded in knowledge base (when available)
- Uses tools (like search) to provide real-time information

#### 4. **Structured Output**
- Always uses Markdown formatting (headings, bolding, lists, tables, code blocks)
- Breaks down complex information into easy-to-scan format
- Maximizes clarity and scannability
- Uses proper syntax highlighting for code blocks

#### 5. **Multimodal Support**
- Can process diverse inputs (text, code, images, audio)
- Responds accordingly based on input type

### Response Rules by Intent

- **General**: Concise, structured, helpful. Always uses Markdown formatting.
- **Social Chat**: One short, professional sentence. Avoids emojis unless contextually appropriate.
- **QA Retrieval**: Clear overview first, then organized bullets with Markdown. Uses tables for comparisons.
- **Coding Help**: Runnable, well-formatted code blocks with syntax highlighting, followed by brief explanation.
- **Editing/Writing**: Improved text first, then key adjustments using structured formatting.
- **Reasoning/Math**: Step-by-step logic with Markdown formatting for equations. Verifies arithmetic carefully.
- **Product Usage**: Plain and confident explanations using structured Markdown formatting.

## 📋 Implementation Checklist

### Visual Design ✅
- [x] Color palette implemented (`#131314`, `#202124`, `#e8eaed`, `#2f3032`)
- [x] Fixed max-width container (`80ch`)
- [x] Response bubbles with rounded corners (`18px`)
- [x] Icon alignment using Flexbox
- [x] Expanding text input field
- [x] Code block styling
- [x] Google Fonts integration (Roboto + Google Sans)
- [x] Proper spacing and padding

### Behavioral Characteristics ✅
- [x] System prompt updated with Gemini-style behavior
- [x] Contextual awareness emphasized
- [x] Direct & analytical tone specified
- [x] Information-driven approach
- [x] Structured output (Markdown) requirements
- [x] Response rules by intent updated
- [x] Conversation history maintenance

## 🚀 Usage

The Gemini-style UI is automatically active when using the DAC chat interface at:
- **Frontend**: `http://localhost:3000/conversations`
- **Backend**: Uses the updated `DAC_SYSTEM_PROMPT` for all conversations

## 📝 Notes

- The visual design matches Gemini's Material Design principles
- The behavioral characteristics ensure responses are professional, structured, and context-aware
- Both visual and behavioral aspects work together to create a cohesive Gemini-like experience
- The system maintains conversation history across all model switches
- Markdown formatting is enforced for all responses to ensure clarity and scannability

## ⚛️ Technical Formatting Rules

### Structured Output for Technical, Mathematical, and Visual Queries

The system prompt includes comprehensive formatting rules for technical content:

#### 1. Mathematical Expressions (LaTeX)
- **Inline math**: Use single dollar signs `$inline$` for formulas within sentences
- **Display/Block equations**: Use double dollar signs `$$display$$` for standalone equations
- **Example**: The energy levels $E_n$ are given by $$E_n = \left(n + \frac{1}{2}\right) \hbar \omega$$

#### 2. Code Blocks (Markdown Code Fences)
- All code MUST be in Markdown code blocks with language identifiers
- Use three backticks (```) followed by language identifier (e.g., ```python, ```javascript)
- Always provide complete, runnable code when possible

#### 3. Data Tables (Markdown Tables)
- Use Markdown tables for structured data, comparisons, or results
- Ensure proper column alignment using `|---`, `:---`, `---:`, or `:---:`

#### 4. Graphing/Plotting (Matplotlib/Seaborn)
- MUST provide full, runnable Python code that generates the plot
- Include all imports, data preparation, plotting commands, and display/show commands
- Do NOT describe the plot; provide the complete code

#### 5. Image Creation/Visuals
- Use the Image Tag format: `<image>description</image>` to signal the UI
- Provide descriptive text explaining what the image should contain

#### 6. Variables/Formulas in Text
- Use inline LaTeX (`$variable$`) for mathematical variables/constants
- Use single backticks for short code variables (e.g., `alpha`, `beta`)

### Modern Aesthetics & Scannability Rules

#### Response Structure
- **Start with Direct Answer**: Every response begins with a concise, one-sentence direct answer or executive summary
- **Use Visual Hierarchy**: Markdown headings (##, ###) to separate major topics, bolding (**word**) for key terms
- **Break Up Text**: Never create large, unbroken paragraphs. Use formatting aggressively to guide the eye
- **Structured Sections**: Follow the summary with organized sections using headings

#### Citation Handling
- **NO Inline Citations**: NEVER use inline references like `[1][3][5]` within the main body
- **Dedicated Section**: Gather ALL references into a separate section at the end titled "Source Information" or "References"
- **Simple Format**: Present sources as a numbered list in the final section

#### Effective List Usage
- Use bullet points (*) or numbered lists (1.) for primary concepts, summaries, or steps
- Keep bullet points concise and impactful
- Avoid long sentences within lists
- Use lists to summarize, not repeat information

#### Tone & Polish
- Professional, analytical, and highly efficient tone
- Direct and concise - avoid conversational filler
- Eliminate redundancy across paragraphs and lists

### Critical Formatting Requirements
- Always use proper Markdown syntax for code blocks (three backticks + language identifier)
- Always use LaTeX for mathematical expressions (single $ for inline, double $$ for display)
- Always provide complete, runnable code for graphs and plots
- Always use Markdown tables for structured data comparisons
- Never mix formatting styles
- Never use inline citations - always move references to the end

## 🔄 Future Enhancements

Potential improvements:
- Add LaTeX rendering support in the frontend (currently displays as raw LaTeX)
- Implement image/audio input processing
- Add real-time search integration
- Enhance multimodal capabilities
- Add more granular tone controls per conversation

