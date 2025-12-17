"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Question {
  id: string;
  text: string;
  options: string[];
  correct_answer: string;
}

interface QuizResponse {
  question_id: string;
  user_answer: string;
  is_correct: boolean;
}

interface QuizBlockProps {
  messageId: string;
  questions: Question[];
  status: string;
  responses?: QuizResponse[];
  onSubmit: (responses: Array<{ question_id: string; user_answer: string }>) => void;
}

export function QuizBlock({
  questions,
  status,
  responses,
  onSubmit,
}: QuizBlockProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const isCompleted = status === "completed";

  const handleSelect = (questionId: string, answer: string) => {
    if (isCompleted) return;
    setAnswers((prev) => ({ ...prev, [questionId]: answer }));
  };

  const handleSubmit = () => {
    const submissionResponses = questions.map((q) => ({
      question_id: q.id,
      user_answer: answers[q.id] || "",
    }));
    onSubmit(submissionResponses);
  };

  const allAnswered = questions.every((q) => answers[q.id]);

  const getResponseForQuestion = (questionId: string) => {
    return responses?.find((r) => r.question_id === questionId);
  };

  return (
    <div className="my-4 ml-0 max-w-[80%] rounded-lg border bg-zinc-50 p-4 dark:bg-zinc-900">
      <p className="mb-4 font-medium">Quick check:</p>

      {questions.map((question, index) => {
        const response = getResponseForQuestion(question.id);

        return (
          <div key={question.id} className="mb-4">
            <p className="mb-2 font-medium">
              {index + 1}. {question.text}
            </p>
            <div className="space-y-2">
              {question.options.map((option) => {
                const letter = option.charAt(0);
                const isSelected = answers[question.id] === letter;
                const wasSubmitted = response?.user_answer === letter;
                const isCorrectAnswer = question.correct_answer === letter;

                let optionClass = "border-zinc-200 dark:border-zinc-700";
                if (isCompleted && response) {
                  if (isCorrectAnswer) {
                    optionClass = "border-green-500 bg-green-50 dark:bg-green-900/20";
                  } else if (wasSubmitted && !response.is_correct) {
                    optionClass = "border-red-500 bg-red-50 dark:bg-red-900/20";
                  }
                } else if (isSelected) {
                  optionClass = "border-zinc-900 dark:border-zinc-100";
                }

                return (
                  <button
                    key={option}
                    onClick={() => handleSelect(question.id, letter)}
                    disabled={isCompleted}
                    className={cn(
                      "w-full rounded-lg border p-3 text-left transition-colors",
                      optionClass,
                      !isCompleted && "hover:bg-zinc-100 dark:hover:bg-zinc-800"
                    )}
                  >
                    {option}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}

      {!isCompleted && (
        <Button
          onClick={handleSubmit}
          disabled={!allAnswered}
          className="mt-2"
        >
          Check Answers
        </Button>
      )}

      {isCompleted && responses && (
        <div className="mt-4 text-sm">
          <p className="font-medium">
            Score: {responses.filter((r) => r.is_correct).length} / {questions.length}
          </p>
        </div>
      )}
    </div>
  );
}
