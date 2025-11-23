"""
Patch to integrate BehaviorCodeGenerator into CodeGenerationService.

This patch adds behavior code generation capabilities to the existing
code generation pipeline.
"""

def integrate_behavior_generator(code_generation_service_file: str):
    """
    Adds BehaviorCodeGenerator integration to CodeGenerationService.

    Modifications:
    1. Add import for BehaviorCodeGenerator
    2. Initialize behavior generator in __init__
    3. Call behavior generator in generate_from_requirements
    """

    # Read current file
    with open(code_generation_service_file, 'r') as f:
        lines = f.readlines()

    # 1. Add import after other imports (around line 67)
    import_line = "from src.services.behavior_code_generator import BehaviorCodeGenerator\n"
    import_index = None
    for i, line in enumerate(lines):
        if "from src.cognitive.signatures.semantic_signature" in line:
            import_index = i + 1
            break

    if import_index:
        lines.insert(import_index, import_line)
        lines.insert(import_index + 1, "\n")

    # 2. Initialize behavior generator in __init__ (around line 180)
    init_lines = [
        "        # Initialize Behavior Code Generator\n",
        "        self.behavior_generator = BehaviorCodeGenerator()\n",
        "        logger.info('Behavior code generator initialized')\n",
        "\n"
    ]

    init_index = None
    for i, line in enumerate(lines):
        if "# Initialize PromptBuilder" in line:
            init_index = i
            break

    if init_index:
        for j, init_line in enumerate(init_lines):
            lines.insert(init_index + j, init_line)

    # 3. Add behavior generation after pattern composition (around line 390)
    behavior_gen_lines = [
        "\n",
        "            # Generate behavior code (workflows, state machines, validators)\n",
        "            if app_ir and app_ir.behavior_model:\n",
        "                logger.info('Generating behavior code from BehaviorModelIR')\n",
        "                behavior_files = self.behavior_generator.generate_business_logic(app_ir.behavior_model)\n",
        "                \n",
        "                logger.info(\n",
        "                    'Generated behavior code',\n",
        "                    extra={\n",
        "                        'files_count': len(behavior_files),\n",
        "                        'workflows': len([f for f in behavior_files if 'workflows' in f]),\n",
        "                        'state_machines': len([f for f in behavior_files if 'state_machines' in f]),\n",
        "                        'validators': len([f for f in behavior_files if 'validators' in f]),\n",
        "                        'event_handlers': len([f for f in behavior_files if 'events' in f]),\n",
        "                    }\n",
        "                )\n",
        "                \n",
        "                # Add behavior files to the generated files dict\n",
        "                files_dict.update(behavior_files)\n",
        "            else:\n",
        "                logger.info('No BehaviorModelIR found, skipping behavior generation')\n",
        "\n"
    ]

    # Find where to insert behavior generation (after llm_generated update)
    behavior_index = None
    for i, line in enumerate(lines):
        if "files_dict.update(llm_generated)" in line:
            behavior_index = i + 1
            break

    if behavior_index:
        for j, behavior_line in enumerate(behavior_gen_lines):
            lines.insert(behavior_index + j, behavior_line)

    # Write modified file
    with open(code_generation_service_file, 'w') as f:
        f.writelines(lines)

    return True


if __name__ == "__main__":
    # Apply patch
    service_file = "/home/kwar/code/agentic-ai/src/services/code_generation_service.py"
    if integrate_behavior_generator(service_file):
        print("Successfully integrated BehaviorCodeGenerator!")
    else:
        print("Failed to integrate BehaviorCodeGenerator")