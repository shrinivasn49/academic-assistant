
import { Component, EventEmitter, Output } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';

import {
  AcademicAssistantService,
  DocumentUploadResponse
} from '../../services/academic-assistant.service';

@Component({
  selector: 'app-document-upload',
  templateUrl: './document-upload.component.html',
  styleUrls: ['./document-upload.component.scss']
})
export class DocumentUploadComponent {

  @Output() documentUploaded = new EventEmitter<{
    documentId: string;
    fileName: string;
  }>();

  @Output() documentCleared = new EventEmitter<void>();

  selectedFile: File | null = null;

  isUploading = false;
  uploadSuccess = false;

  errorMessage = '';
  successMessage = '';

  documentId = '';

  // PDF metadata
  pageCount = 0;
  chunkCount = 0;

  readonly maxFileSize = 10 * 1024 * 1024;

  constructor(
    private academicAssistantService: AcademicAssistantService
  ) {}

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];

    this.resetMessages();

    if (!file) {
      return;
    }

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      this.errorMessage = 'Only PDF files are supported.';
      this.selectedFile = null;
      input.value = '';
      return;
    }

    if (file.size > this.maxFileSize) {
      this.errorMessage = 'File size must not exceed 10 MB.';
      this.selectedFile = null;
      input.value = '';
      return;
    }

    // Clear previous document information.
    this.documentId = '';
    this.pageCount = 0;
    this.chunkCount = 0;

    this.documentCleared.emit();

    this.selectedFile = file;
  }

  uploadDocument(): void {
    if (!this.selectedFile || this.isUploading) {
      return;
    }

    this.resetMessages();
    this.isUploading = true;

    const file = this.selectedFile;

    this.academicAssistantService.uploadDocument(file).subscribe({

      next: (response: DocumentUploadResponse) => {
        this.isUploading = false;

        const documentId = response?.data?.document_id;

        if (!documentId) {
          this.uploadSuccess = false;
          this.errorMessage =
            'PDF uploaded, but document ID was not returned by the API.';
          return;
        }

        this.documentId = documentId;
        this.uploadSuccess = true;

        // Populate PDF metadata from the API response.
        this.pageCount = response.data.page_count ?? 0;

        this.chunkCount =
          response.data.index?.total_chunks ??
          response.data.total_chunks ??
          0;

        this.successMessage =
          response.message || 'PDF uploaded successfully.';

        this.documentUploaded.emit({
          documentId: this.documentId,
          fileName: file.name
        });
      },

      error: (error: HttpErrorResponse) => {
        this.isUploading = false;
        this.uploadSuccess = false;

        this.errorMessage =
          error.error?.detail ||
          error.error?.message ||
          'PDF upload failed. Please try again.';
      }
    });
  }

  removeFile(): void {
    if (this.isUploading) {
      return;
    }

    this.selectedFile = null;
    this.documentId = '';

    this.pageCount = 0;
    this.chunkCount = 0;

    this.resetMessages();
    this.documentCleared.emit();
  }

  private resetMessages(): void {
    this.errorMessage = '';
    this.successMessage = '';
    this.uploadSuccess = false;
  }
}
