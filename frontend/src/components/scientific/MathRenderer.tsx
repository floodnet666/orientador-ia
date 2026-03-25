import React, { useEffect, useRef } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';

interface Props {
    formula: string;
    displayMode?: boolean;  // true = bloco centrado; false = inline
    className?: string;
}

export function MathRenderer({ formula, displayMode = false, className }: Props) {
    const ref = useRef<HTMLSpanElement>(null);

    useEffect(() => {
        if (!ref.current) return;
        try {
            katex.render(formula, ref.current, {
                displayMode,
                throwOnError: false,
                errorColor: '#fb7185',
                trust: false,  // NUNCA true — previne XSS
            });
        } catch (e) {
            if (ref.current) {
                ref.current.textContent = formula; // fallback: mostra texto raw
            }
        }
    }, [formula, displayMode]);

    return <span ref={ref} className={className} />;
}

// Utilitário: detecta e divide texto com fórmulas LaTeX
// Padrões suportados: $$bloco$$ e $inline$
export function renderTextWithMath(text: string): React.ReactNode[] {
    if (!text) return [];
    
    // Limpeza de sinais técnicos internos (como <canvas_signal />)
    const cleanText = text.replace(/<canvas_signal[^>]*\/>/g, '').trim();
    if (!cleanText) return [];

    // Split por blocos $$...$$ e inline $...$
    const parts = cleanText.split(/(\$\$[\s\S]+?\$\$|\$[^\$]+?\$)/g);
    
    return parts.map((part, i) => {
        if (part.startsWith('$$') && part.endsWith('$$')) {
            return <MathRenderer key={i} formula={part.slice(2, -2)} displayMode />;
        }
        if (part.startsWith('$') && part.endsWith('$')) {
            return <MathRenderer key={i} formula={part.slice(1, -1)} />;
        }
        return <span key={i}>{part}</span>;
    });
}

