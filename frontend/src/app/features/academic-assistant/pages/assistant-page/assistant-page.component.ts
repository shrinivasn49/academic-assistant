
import { Component } from '@angular/core';

@Component({
  selector: 'app-assistant-page',
  templateUrl: './assistant-page.component.html',
  styleUrls: ['./assistant-page.component.scss']
})
export class AssistantPageComponent {

  documentId = '';
  documentFileName = '';

  onDocumentUploaded(event: {
    documentId: string;
    fileName: string;
  }): void {
    this.documentId = event.documentId;
    this.documentFileName = event.fileName;
  }

  onDocumentCleared(): void {
    this.documentId = '';
    this.documentFileName = '';
  }

}
