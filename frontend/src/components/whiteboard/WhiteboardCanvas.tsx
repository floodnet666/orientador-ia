import React, { useCallback, useImperativeHandle, forwardRef } from 'react';
import { Tldraw, Editor, createShapeId, TLShapeId, toRichText } from 'tldraw';
import { useProjectStore, CanvasState } from '@/store/project';
import { projectsApi } from '@/lib/api';
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
                richText: toRichText(`[${action.sourceAlma ?? '?'}]\n${action.label}`),
                size: 'm',
                color: _almaColor(action.sourceAlma),
                textAlign: 'middle',
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
                richText: toRichText(action.relation ?? ''),
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
          onMount={(editor) => { 
            editorRef.current = editor;
            
            // Load persistent state if exists
            const canvas = useProjectStore.getState().canvas;
            if (canvas.whiteboard) {
              try {
                console.log('[TLDRAW] Loading snapshot from DB');
                editor.loadSnapshot(canvas.whiteboard);
              } catch (e) {
                console.error('[TLDRAW] Snapshot load fail', e);
              }
            }

            // Sync changes back to server
            let saveTimeout: any = null;
            editor.store.listen((entry) => {
              if (entry.source === 'user') {
                if (saveTimeout) clearTimeout(saveTimeout);
                saveTimeout = setTimeout(async () => {
                  const snapshot = editor.getSnapshot();
                  const projectId = useProjectStore.getState().canvas ? (window as any).activeProjectId : null;
                  if (projectId) {
                    console.log('[TLDRAW] Auto-saving manually...');
                    await projectsApi.patchCanvas(projectId, 'whiteboard', snapshot);
                  }
                }, 3000); // 3s debounce
              }
            });
        }}
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

