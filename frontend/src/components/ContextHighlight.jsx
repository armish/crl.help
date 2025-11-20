/**
 * ContextHighlight component for displaying search context with highlighted matches.
 *
 * Renders a snippet of text with:
 * - Text before the match (with ellipsis if truncated)
 * - Highlighted match term
 * - Text after the match (with ellipsis if truncated)
 */

export default function ContextHighlight({ snippet }) {
  if (!snippet) {
    return null;
  }

  const { before, match, after } = snippet;

  return (
    <p className="text-sm text-gray-700 leading-relaxed">
      {before && (
        <span className="text-gray-600">
          {before}
        </span>
      )}
      <mark className="bg-yellow-200 px-1 font-medium text-gray-900">
        {match}
      </mark>
      {after && (
        <span className="text-gray-600">
          {after}
        </span>
      )}
    </p>
  );
}
