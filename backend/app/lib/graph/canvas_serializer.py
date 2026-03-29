def serialize_canvas_for_prompt(canvas_nodes: list[dict]) -> str:
    """
    Converte o estado do canvas num bloco de texto para injeção em prompts.
    Retorna string vazia se o canvas estiver vazio.
    """
    if not canvas_nodes:
        return ""

    type_labels = {
        "concept":   "📌 Conceitos",
        "argument":  "💬 Argumentos",
        "reference": "📚 Referências",
        "question":  "❓ Questões em Aberto",
        "method":    "🔬 Metodologia",
    }

    by_type: dict[str, list] = {}
    for node in canvas_nodes:
        t = node.get("node_type", "concept")
        by_type.setdefault(t, []).append(node)

    lines = []
    for node_type, nodes in by_type.items():
        label = type_labels.get(node_type, node_type.capitalize())
        lines.append(f"### {label}")
        for n in nodes:
            lines.append(f"- **{n['label']}**: {n.get('content', '')}")
        lines.append("")

    return "\n".join(lines)
