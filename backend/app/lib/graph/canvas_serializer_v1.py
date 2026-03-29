def serialize_canvas_for_prompt(canvas_nodes: list[dict]) -> str:
    """
    Converte o estado do canvas num bloco de texto estruturado para injeção em prompts.
    Retorna string vazia se o canvas estiver vazio.
    """
    if not canvas_nodes:
        return ""

    lines = ["## Estado do Projeto no Canvas\n"]

    # Agrupa por tipo de nó
    by_type: dict[str, list] = {}
    for node in canvas_nodes:
        # Pega o tipo, default para 'concept'
        t = node.get("node_type") or node.get("type", "concept")
        by_type.setdefault(t, []).append(node)

    type_labels = {
        "concept":    "📌 Conceitos",
        "argument":   "💬 Argumentos",
        "reference":  "📚 Referências",
        "question":   "❓ Questões em Aberto",
        "method":     "🔬 Metodologia",
        "tema":       "🎯 Tema",
        "problema":   "❓ Problema",
        "objetivo":   "🚀 Objetivos"
    }

    # Ordenação sugerida de importância
    order = ["tema", "problema", "objetivo", "method", "concept", "argument", "reference", "question"]
    
    # Adiciona os tipos conhecidos na ordem
    for node_type in order:
        if node_type in by_type:
            nodes = by_type[node_type]
            label = type_labels.get(node_type, node_type.capitalize())
            lines.append(f"### {label}")
            for n in nodes:
                # Usa label e content (ou texto do nó)
                node_label = n.get("label") or n.get("id", "Nó")
                node_content = n.get("content") or n.get("text", "")
                if node_content:
                    lines.append(f"- **{node_label}**: {node_content}")
                else:
                    lines.append(f"- **{node_label}**")
            lines.append("")

    # Adiciona tipos extras não mapeados na ordem
    for node_type, nodes in by_type.items():
        if node_type not in order:
            label = type_labels.get(node_type, node_type.capitalize())
            lines.append(f"### {label}")
            for n in nodes:
                node_label = n.get("label") or n.get("id", "Nó")
                node_content = n.get("content") or n.get("text", "")
                if node_content:
                    lines.append(f"- **{node_label}**: {node_content}")
                else:
                    lines.append(f"- **{node_label}**")
            lines.append("")

    return "\n".join(lines)
