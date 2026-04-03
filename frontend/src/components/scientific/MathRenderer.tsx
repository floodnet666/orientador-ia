import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { FileText, ExternalLink } from 'lucide-react';

interface CitationLinkProps {
    href?: string;
    children: React.ReactNode;
}

const CitationLink = ({ href, children }: CitationLinkProps) => {
    const isPdf = typeof children === 'string' && children.toLowerCase().includes('pdf');
    
    return (
        <a 
            href={href} 
            target="_blank" 
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 hover:bg-indigo-500/20 hover:border-indigo-500/40 transition-all text-indigo-300 text-xs font-bold my-1 mx-0.5 group no-underline"
        >
            {isPdf ? <FileText size={12} className="group-hover:scale-110 transition-transform" /> : <ExternalLink size={12} className="group-hover:scale-110 transition-transform" />}
            <span>{children}</span>
        </a>
    );
};

export function renderTextWithMath(text: string): React.ReactNode {
    if (!text) return null;
    
    // Limpeza de sinais técnicos internos
    const cleanText = text.replace(/<canvas_signal[^>]*\/>/g, '').trim();
    if (!cleanText) return null;

    return (
        <div className="prose prose-invert max-w-none prose-p:leading-relaxed prose-p:my-1.5 prose-strong:text-indigo-200 markdown-content">
            <ReactMarkdown 
                remarkPlugins={[remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{
                    // Customizar links para virarem botões premium
                    a: ({ node, ...props }) => <CitationLink {...props as any} />,
                    // Remover margens excessivas de parágrafos para manter o chat denso
                    p: ({ node, ...props }) => <p {...props} className="mb-2 last:mb-0 leading-relaxed text-slate-100" />,
                    // Listas compactas
                    ul: ({ node, ...props }) => <ul {...props} className="list-disc list-inside space-y-1 mb-2" />,
                    ol: ({ node, ...props }) => <ol {...props} className="list-decimal list-inside space-y-1 mb-2" />,
                    // Fortalecer negritos acadêmicos
                    strong: ({ node, ...props }) => <strong {...props} className="text-indigo-200 font-bold" />,
                }}
            >
                {cleanText}
            </ReactMarkdown>
        </div>
    );
}

// Mantendo export para retrocompatibilidade se necessário, mas renderTextWithMath agora é o entrypoint principal
export { MathRenderer } from './MathRenderer_v1';
