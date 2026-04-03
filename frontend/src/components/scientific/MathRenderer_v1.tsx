import React, { useEffect, useRef } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';

interface Props {
    formula: string;
    displayMode?: boolean; 
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
                trust: false,
            });
        } catch (e) {
            if (ref.current) {
                ref.current.textContent = formula;
            }
        }
    }, [formula, displayMode]);

    return <span ref={ref} className={className} />;
}
