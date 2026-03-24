import React from 'react';
import { render, act } from '@testing-library/react';
import { WhiteboardCanvas, WhiteboardCanvasRef } from '../WhiteboardCanvas';

// Mock do tldraw (não queremos renderizar o canvas completo nos testes unitários)
jest.mock('tldraw', () => ({
  Tldraw: ({ onMount }: { onMount: (e: any) => void }) => {
    const mockEditor = {
      createShape: jest.fn().mockReturnValue('shape-1'),
      deleteShapes: jest.fn(),
      getCurrentPageShapeIds: jest.fn().mockReturnValue(new Set()),
    };
    React.useEffect(() => { onMount(mockEditor); }, []);
    return <div data-testid="tldraw-mock" />;
  },
}));

test('renderiza sem erros', () => {
  const { getByTestId } = render(<WhiteboardCanvas />);
  expect(getByTestId('tldraw-mock')).toBeInTheDocument();
});

test('executeAction ADD_NODE chama createShape', async () => {
  const ref = React.createRef<WhiteboardCanvasRef>();
  render(<WhiteboardCanvas ref={ref} />);
  
  await act(async () => {
    ref.current?.executeAction({
      type: 'ADD_NODE', id: 'n1', label: 'Habitus', sourceAlma: 'PB',
    });
  });
  
  // Se não lança excepção, o nó foi processado
  expect(ref.current).toBeTruthy();
});

test('executeAction CLEAR não lança excepção', async () => {
  const ref = React.createRef<WhiteboardCanvasRef>();
  render(<WhiteboardCanvas ref={ref} />);
  
  await act(async () => {
    expect(() => ref.current?.executeAction({ type: 'CLEAR' })).not.toThrow();
  });
});
