# Frontend

Next.js 16 app with a Kanban board. Currently a standalone demo with no backend or auth.

## Stack

- Next.js 16, React 19, TypeScript 5
- Tailwind CSS v4 (utility-first, CSS variables for design tokens)
- @dnd-kit for drag and drop (PointerSensor, closestCorners collision)
- Vitest + Testing Library for unit tests, Playwright for E2E

## Structure

- src/app/ -- Next.js app router (layout, page, globals.css)
- src/components/ -- Kanban UI components
- src/lib/ -- Data model, types, and pure logic functions
- src/test/ -- Test setup and type definitions
- tests/ -- Playwright E2E specs

## Components

**KanbanBoard.tsx** -- Main container. Holds all board state (useState). Sets up DndContext with PointerSensor and closestCorners. Handles dragStart, dragEnd, renameColumn, addCard, deleteCard. Renders a 5-column grid with DragOverlay for drag previews. Decorative gradient backgrounds.

**KanbanColumn.tsx** -- Single column. Uses useDroppable as a drop target. Editable title input for renaming. Contains SortableContext with verticalListSortingStrategy. Shows card count and empty state.

**KanbanCard.tsx** -- Draggable card. Uses useSortable hook. Displays title + details. Has a remove button. Visual feedback (opacity/shadow) during drag.

**KanbanCardPreview.tsx** -- Presentational component rendered inside DragOverlay during drag operations.

**NewCardForm.tsx** -- Inline form toggled by "Add a card" button. Title input + details textarea. Validates non-empty title.

## Data Model (src/lib/kanban.ts)

Types: Card (id, title, details), Column (id, title, cardIds), BoardData (cards map, columns map, columnOrder).

initialData: 5 columns (Backlog, Discovery, In Progress, Review, Done) with 8 sample cards.

Functions: createId(prefix), moveCard(board, activeId, overId), findColumnId(board, cardId), isColumnId(board, id).

## Tests

- src/lib/kanban.test.ts -- 3 unit tests for moveCard logic
- src/components/KanbanBoard.test.tsx -- 3 unit tests (render, rename, add/delete)
- tests/kanban.spec.ts -- 3 Playwright E2E tests (load, add card, drag)

## Scripts (package.json)

- dev / build / start -- Next.js commands
- test:unit -- vitest
- test:e2e -- playwright test
- test:all -- both

## Current State

No backend integration. No authentication. No API calls. All state is local to the React component. This is a working frontend demo that will be converted to a static export and connected to the FastAPI backend.
