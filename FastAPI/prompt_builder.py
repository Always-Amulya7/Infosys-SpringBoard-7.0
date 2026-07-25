def build_daily_prompt(context: dict) -> str:
    return (
        "Analyze the following productivity data and provide a structured insight report.\n\n"
        f"Working Time: {context.get('working_time', 0)} seconds\n"
        f"Idle Time: {context.get('idle_time', 0)} seconds\n"
        f"Distraction Time: {context.get('distraction_time', 0)} seconds\n"
        f"Focus Score: {context.get('focus_score', 0)}%\n"
        f"Productivity Score: {context.get('productivity_score', 0)}%\n"
        f"Total Time: {context.get('total_time', 0)} seconds\n"
        f"Most Distracting Websites: {', '.join(context.get('most_distracting_websites', []))}\n"
        f"Most Productive Applications: {', '.join(context.get('most_productive_applications', []))}\n\n"
        "Applications/Websites usage (name, time seconds):\n"
    ) + "\n".join(
        f"- {item.get('name', item.get('domain', 'Unknown'))}: {item.get('time', 0)} seconds"
        for item in context.get("applications", context.get("website_usage", []))[:20]
    ) + "\n\n" + (
        "Return a concise analysis in plain text with the following exactly in order:\n"
        "1. Summary\n"
        "2. Productivity Analysis\n"
        "3. Most distracting websites\n"
        "4. Most productive applications\n"
        "5. Areas of improvement\n"
        "6. Recommendations\n"
        "7. Motivational message\n"
        "8. Focus score explanation\n\n"
        "Format each section with a clear heading."
    )
