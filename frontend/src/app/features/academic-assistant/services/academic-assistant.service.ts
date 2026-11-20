
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface DocumentSource {
  page_number: number;
  similarity_score: number;
  text: string;
}

export interface DocumentUploadResponse {
  success: boolean;
  message: string;
  data: {
    document_id: string;
    filename?: string;
    page_count?: number;
    total_chunks?: number;
    index?: {
      status: string;
      total_chunks: number;
      embedding_dimension: number;
    };
  };
}

export interface DocumentAnswerResponse {
  success: boolean;
  document_id: string;
  question: string;
  answer: string;
  sources: DocumentSource[];
  model: string;
}

export interface DocumentSearchResponse {
  success: boolean;
  question: string;
  results: DocumentSource[];
}

@Injectable({
  providedIn: 'root'
})
export class AcademicAssistantService {

  // Keep 8001 if your FastAPI server is running on port 8001.
  private readonly apiUrl = 'http://127.0.0.1:8001/api/documents';

  constructor(private http: HttpClient) {}

  uploadDocument(file: File): Observable<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    return this.http.post<DocumentUploadResponse>(
      `${this.apiUrl}/upload`,
      formData
    );
  }

  askQuestion(
    documentId: string,
    question: string,
    topK: number = 5
  ) {
    return this.http.post<DocumentAnswerResponse>(
      `${this.apiUrl}/${documentId}/ask`,
      { question, top_k: topK }
    );
  }
  
  searchDocument(
    documentId: string,
    question: string,
    topK: number = 5
  ) {
    return this.http.post<DocumentSearchResponse>(
      `${this.apiUrl}/${documentId}/search`,
      { question, top_k: topK }
    );
  }
}
