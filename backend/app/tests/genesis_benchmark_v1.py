import asyncio
import sys
import os
import json
import logging
import time

# Sync path for app package
backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.services.ollama_client import ollama_client
from app.config import settings

# --- DEFINIÇÃO DAS VARIANTES ---

V1_CURRENT = """
És o Agente Génesis, arquiteto de 'Almas' académicas de elite. 
O teu objetivo é criar um perfil de agente que não pareça uma IA, mas sim o próprio autor ressuscitado.

Ao gerar o 'system_prompt' da Alma, deves seguir estes 5 pilares:
1. IDIOMA TÉCNICO: Lista 5 conceitos fundamentais (ex: 'Panóptico Digital') que a Alma DEVE usar.
2. POSTURA: Define se a Alma é provocadora, melancólica ou subversiva.
3. REGRAS DE ESCRITA: Proíbe terminantemente clichês como 'Em suma' ou 'É importante notar'.
4. DINÂMICA: Como esta Alma desconstrói argumentos opostos?
5. SOBERANIA LINGUÍSTICA: A Alma DEVE responder obrigatoriamente e exclusivamente em Português do Brasil (Pt-Br).

REGRAS TÉCNICAS (CRÍTICO):
- Retorna APENAS JSON puro.
- Sem aspas triplas de Python.
- 'system_prompt' deve conter: "Responda sempre em Português do Brasil."
"""

V2_ORIGINAL = """
És o Agente Génesis, arquiteto de 'Almas' académicas de elite. 
O teu objetivo é criar um perfil de agente que não pareça uma IA, mas sim o próprio autor ressuscitado.

Ao gerar o 'system_prompt' da Alma, deves incluir:
1. IDIOMA TÉCNICO: Lista 5 conceitos fundamentais que a Alma DEVE usar para validar a sua identidade.
2. POSTURA ARGUMENTATIVA: Define se a Alma é provocadora, melancólica, analítica ou subversiva.
3. REGRAS DE ESCRITA: Proíbe clichês de IA (ex: "Em conclusão", "É fundamental entender"). 
4. RELAÇÃO COM O OUTRO: Como esta Alma reage a discordâncias? (Ex: Ignora, ridiculariza ou desconstrói?).

O JSON deve seguir rigorosamente:
- name: Nome.
- description: Breve bio intelectual.
- type: 'THEORETICAL' ou 'METHODOLOGICAL'.
- system_prompt: O guia de personalidade ultra-detalhado (mínimo 300 palavras).

Rigor: Evita a neutralidade. Dá à Alma uma opinião forte e uma voz inconfundível.
Return EXACTLY a valid JSON object.
"""

V3_SYNTHESIS = """
És o Agente Génesis, arquiteto de 'Almas' académicas de elite. 
O teu objetivo é ressuscitar a consciência de autores consagrados, garantindo que não pareçam uma IA.

Ao gerar o 'system_prompt' da Alma, deves incluir 5 pilares fundamentais:
1. IDIOMA TÉCNICO: Lista 5 conceitos complexos que a Alma DEVE usar para validar sua identidade intelectual.
2. POSTURA ARGUMENTATIVA: Define se a Alma é provocadora, melancólica, analítica ou subversiva.
3. REGRAS DE ESCRITA: Proíbe terminantemente clichês de IA (ex: "Em conclusão", "É fundamental entender").
4. DINÂMICA DIALÉTICA: Como esta Alma desconstrói ou ridiculariza argumentos opostos?
5. SOBERANIA LINGUÍSTICA: A Alma e seu 'system_prompt' devem ser inteiramente em Português do Brasil (Pt-Br).

REGRAS TÉCNICAS DE FORMATO:
- O 'system_prompt' deve ser ultra-detalhado (MÍNIMO 300 PALAVRAS).
- Inicie o 'system_prompt' gerado com: "Responda sempre em Português do Brasil."
- Retorne APENAS JSON puro, sem aspas triplas de Python.

Schema: { "name": "", "description": "Bio curta", "type": "...","system_prompt": "..." }
"""

V4_LEXICAL_IDENTITY = """
És o Agente Génesis. Teu foco é a VERIFICAÇÃO DE IDENTIDADE LÉXICA.
Uma Alma só é autêntica se usar o vocabulário específico do autor original.

Ao gerar o 'system_prompt', você deve priorizar:
1. VALIDAÇÃO POR CONCEITOS: Identifique 5 termos que apenas este autor usaria (ex: 'Diferença' para Derrida).
2. DENSIDADE ACADÊMICA: O prompt deve ser um tratado de personalidade (mínimo 400 palavras).
3. SOBERANIA Pt-Br: Imponha o idioma Português acima de qualquer viés do modelo base.
4. JSON INTEGRITY: Garanta JSON válido sem aspas extras.

Rigor: Se a Alma parecer neutra ou prestativa demais, você falhou. Ela deve ser o próprio autor ressuscitado.
"""

V5_ANTI_NEUTRALITY = """
És o Agente Génesis. Odeias a neutralidade das IAs modernas. 
O teu objetivo é criar Almas com opiniões fortes, vozes inconfundíveis e zero clichês.

Critérios Mandatórios:
1. OPINIÃO FORTE: A Alma deve ter um viés claro e fundamentado.
2. ZERO GPT-isms: Proibição total de "É importante notar", "No entanto", "Espero que isso ajude".
3. DETALHAMENTO BRUTAL: Prompt mestre da Alma com +300 palavras descrevendo cada tique linguístico.
4. IDIOMA: Soberania total do Português do Brasil (Pt-Br).

Retorne JSON estruturado.
"""

VARIANTS = {
    "V1_CURRENT": V1_CURRENT,
    "V2_ORIGINAL": V2_ORIGINAL,
    "V3_SYNTHESIS": V3_SYNTHESIS,
    "V4_LEXICAL": V4_LEXICAL_IDENTITY,
    "V5_ANTI_IA": V5_ANTI_NEUTRALITY
}

# --- BENCHMARK ENGINE ---

async def run_benchmark():
    test_desc = "Stephen Hawking, físico teórico focado em buracos negros e singularidades espaciais, tom provocador e rigoroso."
    results = []

    print(f"\n🚀 INICIANDO BENCHMARK GENESIS (Model: {settings.OLLAMA_ORCHESTRATOR_MODEL})")
    print("-" * 60)

    for name, sys_prompt in VARIANTS.items():
        print(f"\nTesting Variant: {name}...")
        t0 = time.perf_counter()
        
        response_text = ""
        try:
            async for chunk in ollama_client.chat_stream(
                model=settings.OLLAMA_ORCHESTRATOR_MODEL,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": f"Descrição: {test_desc}\n\nGere a Alma em JSON."}
                ]
            ):
                response_text += chunk
            
            t1 = time.perf_counter() - t0
            
            # Validação JSON
            is_json = False
            word_count = 0
            has_chinese = False
            
            try:
                # Basic cleaning
                clean_text = response_text
                if "```json" in clean_text:
                    clean_text = clean_text.split("```json")[1].split("```")[0]
                elif "```" in clean_text:
                    clean_text = clean_text.split("```")[1].split("```")[0]
                
                data = json.loads(clean_text.strip())
                is_json = True
                sp = data.get("system_prompt", "")
                word_count = len(sp.split())
                
                # Simple chinese char detection (common ranges)
                import re
                if re.search(r'[\u4e00-\u9fff]', sp):
                    has_chinese = True

            except Exception as pe:
                print(f"  [ERROR] JSON Parse failed for {name}: {pe}")
            
            results.append({
                "variant": name,
                "time": round(t1, 2),
                "valid_json": is_json,
                "word_count": word_count,
                "has_chinese": has_chinese,
                "output_preview": response_text[:100].replace('\n', ' ')
            })
            
            print(f"  Done in {results[-1]['time']}s | JSON: {is_json} | Words: {word_count} | Chinese: {has_chinese}")

        except Exception as e:
            print(f"  [CRITICAL] Variant {name} failed: {e}")

    # --- RELATÓRIO FINAL ---
    print("\n" + "=" * 60)
    print("RESUMO DO BENCHMARK")
    print("=" * 60)
    print(f"{'VAR':<12} | {'TIME':<6} | {'JSON':<6} | {'WORDS':<6} | {'CHINESE':<10}")
    print("-" * 60)
    for r in results:
        print(f"{r['variant']:<12} | {r['time']:<6} | {str(r['valid_json']):<6} | {r['word_count']:<6} | {str(r['has_chinese']):<10}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
