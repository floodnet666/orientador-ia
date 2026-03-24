import React, { useCallback, useImperativeHandle, forwardRef } from 'react';
import { Tldraw, Editor, createShapeId, TLShapeId } from 'tldraw';
import { useActionStream } from '@/hooks/useActionStream';
import 'tldraw/tldraw.css';

export interface WhiteboardAction {
  type:    'ADD_NODE' | 'ADD_EDGE' | 'CLEAR';
  id?:     string;
  label?:  string;
  conceptType?: string;
  sourceAlma?:  string;
  sourceId?: string;
  targetId?: string;
  relation?: string;
}

export interface WhiteboardCanvasRef {
  executeAction: (action: WhiteboardAction) => void;
}

interface Props {
  className?: string;
  readOnly?: boolean;
}

// Mapa interno de nodeId -> tldraw shapeId (TLShapeId)
const nodeMap = new Map<string, TLShapeId>();

export const WhiteboardCanvas = forwardRef<WhiteboardCanvasRef, Props>(
  function WhiteboardCanvas({ className, readOnly = false }, ref) {
    const editorRef = React.useRef<Editor | null>(null);

    const executeAction = useCallback((action: WhiteboardAction) => {
      const editor = editorRef.current;
      if (!editor) return;

      switch (action.type) {
        case 'ADD_NODE': {
          if (!action.id || !action.label) return;
          const x = 100 + (nodeMap.size % 4) * 180;
          const y = 100 + Math.floor(nodeMap.size / 4) * 120;
          
          try {
            const shapeId = createShapeId();
            editor.createShape({
              id: shapeId,
              type: 'text',
              x, y,
              props: {
                text: `[${action.sourceAlma ?? '?'}]\n${action.label}`,
                size: 'm',
                color: _almaColor(action.sourceAlma),
                align: 'middle',
              } as any,
            });
            nodeMap.set(action.id, shapeId);
          } catch (e) {
            console.error('Failed to create shape on whiteboard:', e);
          }
          break;
        }
        case 'ADD_EDGE': {
          if (!action.sourceId || !action.targetId) return;
          const fromId = nodeMap.get(action.sourceId);
          const toId   = nodeMap.get(action.targetId);
          if (!fromId || !toId) return;
          
          try {
            editor.createShape({
              type: 'arrow',
              props: {
                start: { type: 'binding', boundShapeId: fromId, isExact: false },
                end:   { type: 'binding', boundShapeId: toId,   isExact: false },
                text:  action.relation ?? '',
                color: 'grey',
              } as any,
            });
          } catch (e) {
            console.error('Failed to create edge on whiteboard:', e);
          }
          break;
        }
        case 'CLEAR': {
          try {
            const shapeIds = Array.from(editor.getCurrentPageShapeIds());
            editor.deleteShapes(shapeIds);
            nodeMap.clear();
          } catch (e) {
            console.error('Failed to clear whiteboard:', e);
          }
          break;
        }
      }
    }, []);

    // Self-subscribe to the Action Stream!
    useActionStream({
      onCanvasNode: (payload) => executeAction({
        type: 'ADD_NODE',
        id: payload.id,
        label: payload.label,
        conceptType: payload.concept_type,
        sourceAlma: payload.source_alma
      }),
      onCanvasEdge: (payload) => executeAction({
        type: 'ADD_EDGE',
        sourceId: payload.source_id,
        targetId: payload.target_id,
        relation: payload.relation
      }),
    });

    useImperativeHandle(ref, () => ({ executeAction }), [executeAction]);

    return (
      <div className={className} style={{ width: '100%', height: '100%' }}>
        <Tldraw
          hideUi={readOnly}
          onMount={(editor) => { editorRef.current = editor; }}
        />
      </div>
    );
  }
);

function _almaColor(alma?: string): 'violet' | 'red' | 'green' | 'blue' {
  const colors: Record<string, 'violet' | 'red' | 'green' | 'blue'> = {
    PB: 'violet',
    MF: 'red',
    PF: 'green',
  };
  return colors[alma ?? ''] ?? 'blue';
}

