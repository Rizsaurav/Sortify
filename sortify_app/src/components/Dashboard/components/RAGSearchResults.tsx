import React from 'react';
import { X, FileText, Sparkles, Clock } from 'lucide-react';
import type { SearchResult } from '../../../api/sorter';

interface RAGSearchResultsProps {
  searchResult: SearchResult;
  query: string;
  onClose: () => void;
}

export const RAGSearchResults: React.FC<RAGSearchResultsProps> = ({
  searchResult,
  query,
  onClose
}) => {
  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-start justify-center pt-20 px-4">
      <div className="bg-card border border-border rounded-lg shadow-2xl max-w-3xl w-full max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-border flex items-center justify-between bg-gradient-to-r from-purple-500/10 to-blue-500/10">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-purple-500" />
            <h2 className="text-lg font-semibold">AI Search Results</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-accent rounded-lg transition-colors"
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Query */}
        <div className="px-4 pt-4 pb-2 bg-accent/30">
          <p className="text-sm text-muted-foreground">Your question:</p>
          <p className="text-base font-medium mt-1">{query}</p>
        </div>

        {/* Answer */}
        <div className="p-4 flex-1 overflow-y-auto">
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-purple-500 mb-2 flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              Answer
            </h3>
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <p className="text-foreground whitespace-pre-wrap leading-relaxed">
                {searchResult.answer}
              </p>
            </div>
          </div>

          {/* Sources */}
          {searchResult.sources && searchResult.sources.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-blue-500 mb-2 flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Sources ({searchResult.sources.length})
              </h3>
              <div className="space-y-2">
                {searchResult.sources.map((source, index) => (
                  <div
                    key={index}
                    className="px-3 py-2 bg-accent rounded-lg border border-border flex items-center gap-2"
                  >
                    <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                    <span className="text-sm">{source}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Metadata */}
          <div className="mt-6 pt-4 border-t border-border">
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <div className="flex items-center gap-1">
                <FileText className="w-3 h-3" />
                <span>{searchResult.chunks_used} chunks analyzed</span>
              </div>
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span>{searchResult.response_time.toFixed(2)}s</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border bg-accent/20">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
