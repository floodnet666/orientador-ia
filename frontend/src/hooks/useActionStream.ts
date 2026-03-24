import { useEffect, useRef } from 'react';

export interface ActionToken {
    type: string;
    payload: any;
}

export interface ActionHandlers {
    onSpotlight?: (payload: any) => void;
    onCanvasNode?: (payload: any) => void;
    onCanvasEdge?: (payload: any) => void;
    onConflict?: (payload: any) => void;
}

export function useActionStream(handlers: ActionHandlers) {
    const handlersRef = useRef(handlers);
    
    useEffect(() => {
        handlersRef.current = handlers;
    });

    useEffect(() => {
        const handleAction = (e: Event) => {
            const customEvent = e as CustomEvent<ActionToken>;
            const token = customEvent.detail;
            if (!token || !token.type) return;

            const h = handlersRef.current;
            switch (token.type) {
                case 'SPOTLIGHT_PDF':
                    h.onSpotlight?.(token.payload);
                    break;
                case 'CANVAS_NODE':
                    h.onCanvasNode?.(token.payload);
                    break;
                case 'CANVAS_EDGE':
                    h.onCanvasEdge?.(token.payload);
                    break;
                case 'CONFLICT_FLAG':
                    h.onConflict?.(token.payload);
                    break;
            }
        };

        window.addEventListener('chat_action_event', handleAction);
        return () => window.removeEventListener('chat_action_event', handleAction);
    }, []);
}
