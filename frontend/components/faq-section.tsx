"use client"

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"

const faqs = [
  {
    question: "What is Syntra?",
    answer:
      "Syntra is a private multi-model AI workspace with unified memory. It gives you access to ChatGPT, Claude, Gemini, Kimi K2, Llama, and more—all in one place. Your data stays encrypted and is never used for training.",
  },
  {
    question: "How does Syntra ensure privacy for user data?",
    answer:
      "Syntra offers encrypted storage, user-controlled deletion, and never trains on your chats or files. Your information is isolated and never repurposed. You can delete any conversation or file at any time, and it will be permanently removed.",
  },
  {
    question: "Who should use Syntra?",
    answer:
      "Syntra is ideal for professionals who need multi-model AI assistance but can't risk data exposure—lawyers, doctors, financial advisors, government officials, journalists, and anyone handling sensitive information.",
  },
  {
    question: "What AI models and tools are available on Syntra?",
    answer:
      "Syntra provides access to leading frontier models including ChatGPT, Claude, Gemini, Kimi K2, and Llama. All models share unified memory so you can switch between them without losing context.",
  },
  {
    question: "What makes Syntra different from ChatGPT or other AI tools?",
    answer:
      "Most AI platforms lock you into a single model and may use your data to improve their systems. Syntra is different: you can use multiple frontier models in the same conversation with shared memory. Your data is encrypted, isolated, and never repurposed. Think of Syntra as your private multi-model AI workspace.",
  },
  {
    question: "Does Syntra store my chats or files?",
    answer:
      "Yes, but only so you can access them securely. Your chats and files are stored encrypted and accessible only to you. They are not analyzed, indexed, or shared with any external service. You can delete any conversation or file at any time, and it will be permanently removed.",
  },
  {
    question: "Are the uploaded documents and files on Syntra also private and encrypted?",
    answer:
      "Yes. You can upload PDFs, DOCX, spreadsheets, images and more for analysis, summarization or creative generation. Your uploads remain encrypted and private, and are never used for training.",
  },
]

export function FAQSection() {
  return (
    <section className="py-20 px-6 border-t border-border">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-foreground mb-4 italic">
            Frequently Asked Questions
          </h2>
          <p className="text-muted-foreground">Everything you need to know about Syntra</p>
        </div>

        <Accordion type="single" collapsible className="space-y-2">
          {faqs.map((faq, index) => (
            <AccordionItem key={index} value={`item-${index}`} className="border-b border-border">
              <AccordionTrigger className="text-left text-foreground hover:no-underline py-6">
                {faq.question}
              </AccordionTrigger>
              <AccordionContent className="text-muted-foreground pb-6">{faq.answer}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  )
}
