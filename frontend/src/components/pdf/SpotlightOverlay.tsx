import React, { useEffect, useRef, useCallback } from 'react';

export interface SpotlightTarget {
    page: number;
    yTop: number;    // 0-1 normalizado
    yBottom: number; // 0-1 normalizado
    keyword?: string;
}

interface Props {
    target: SpotlightTarget | null;
    pdfContainerRef: React.RefObject<HTMLElement | null>;
    durationMs?: number;  // default: 8000
    onExpire?: () => void;
}

export function SpotlightOverlay({ target, pdfContainerRef, durationMs = 8000, onExpire }: Props) {
    const overlayRef = useRef<HTMLDivElement>(null);
    const timerRef   = useRef<ReturnType<typeof setTimeout> | null>(null);

    const clearSpotlight = useCallback(() => {
        if (overlayRef.current) {
            overlayRef.current.style.opacity = '0';
        }
        if (timerRef.current) {
            clearTimeout(timerRef.current);
            timerRef.current = null;
        }
    }, []);

    useEffect(() => {
        if (!target || !pdfContainerRef.current || !overlayRef.current) return;

        const container = pdfContainerRef.current;
        const containerHeight = container.scrollHeight;
        
        // Calcula posição do highlight
        const totalPages = container.querySelectorAll('[data-page-number]').length || 1;
        const pageHeight = containerHeight / totalPages;
        const pageOffset = target.page * pageHeight;
        const highlightTop    = pageOffset + target.yTop    * pageHeight;
        const highlightBottom = pageOffset + target.yBottom * pageHeight;
        const highlightHeight = Math.max(highlightBottom - highlightTop, 30);

        // Posiciona overlay
        const overlay = overlayRef.current;
        overlay.style.top    = `${highlightTop}px`;
        overlay.style.height = `${highlightHeight}px`;
        overlay.style.opacity = '1';

        // Scroll suave até ao highlight
        container.scrollTo({
            top: Math.max(0, highlightTop - 100),
            behavior: 'smooth',
        });

        // Auto-expirar
        clearSpotlight();
        timerRef.current = setTimeout(() => {
            clearSpotlight();
            onExpire?.();
        }, durationMs);

        return () => clearSpotlight();
    }, [target, pdfContainerRef, durationMs, clearSpotlight, onExpire]);

    return (
        <div
            ref={overlayRef}
            aria-hidden="true"
            style={{
                position:        'absolute',
                left:            0,
                right:           0,
                opacity:         0,
                pointerEvents:   'none',
                transition:      'opacity 0.4s ease, top 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
                background:      'rgba(245, 158, 11, 0.18)',
                borderLeft:      '3px solid rgba(245, 158, 11, 0.8)',
                borderRadius:    '2px',
                zIndex:          10,
                boxShadow:       '0 0 20px rgba(245, 158, 11, 0.15)',
            }}
        />
    );
}
