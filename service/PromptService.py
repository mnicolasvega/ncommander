class PromptService:
    def get_formatted_prompt(self, prompt: str) -> str:
        """Format prompt with instructions to guide the LLM."""
        instructions = [
            "Provide a clear, informative answer with medium length",
            "(2-3 sentences, not too brief and not too verbose).",
        ]
        instruction_block = f"Instructions: %s\n" % ('\n'.join(instructions))
        return f"{prompt}\n{instruction_block}\nAnswer:"
