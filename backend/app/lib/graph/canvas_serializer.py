def serialize_canvas_for_prompt(canvas_nodes: list[dict]) -> str:
    """
    Converte o estado do canvas num bloco de texto para injeção em prompts.
    Retorna string vazia se o canvas estiver vazio.
    Focado no novo motor visual (React Flow v8.1.0).
    """
    if not canvas_nodes:
        return ""

    type_labels = {
        "PB": "🎯 Ponto de Batida (Marcos/Objetivos)",
        "MF": "🌊 Mar de Fatos (Evidências/Dados)",
        "PF": "🚀 Ponto de Fuga (Hipóteses/Futuro)",
        "AI": "🤖 Agente Interno (Intervenções/Personas)",
    }

    by_type: dict[str, list[dict]] = {}
    for node in canvas_nodes:
        # Tenta pegar 'type' (React Flow) ou fallback 'node_type'
        t = node.get("type") or node.get("node_type", "PB")
        by_type.setdefault(t, []).append(node)

    lines = ["## ESTADO ATUAL DO WHITEBOARD"]
    
    # Ordem lógica de exibição
    for node_type in ["PB", "MF", "PF", "AI"]:
        nodes = by_type.get(node_type, [])
        if not nodes:
            continue
            
        label = type_labels.get(node_type, node_type)
        lines.append(f"### {label}")
        for n in nodes:
            # Pega label do React Flow 'data.label' ou do node_type direto
            node_label = n.get("data", {}).get("label") or n.get("label", "Sem rótulo")
            lines.append(f"- [{n.get('id', '??')}] **{node_label}**")
        lines.append("")

    return "\n".join(lines)
