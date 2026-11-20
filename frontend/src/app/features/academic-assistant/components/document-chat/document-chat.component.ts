
import {
  Component,
  Input,
  OnChanges,
  SimpleChanges,
  ViewChild,
  ElementRef
} from '@angular/core';

import { HttpErrorResponse } from '@angular/common/http';
import { finalize } from 'rxjs/operators';

import {
  AcademicAssistantService,
  DocumentAnswerResponse,
  DocumentSource
} from '../../services/academic-assistant.service';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: DocumentSource[];
}

@Component({
  selector: 'app-document-chat',
  templateUrl: './document-chat.component.html',
  styleUrls: ['./document-chat.component.scss']
})
export class DocumentChatComponent implements OnChanges {

  @Input() documentId = '';

  @ViewChild('chatMessages')
  private chatMessages?: ElementRef<HTMLDivElement>;

  question = '';
  isLoading = false;
  errorMessage = '';

  messages: ChatMessage[] = [];

  constructor(
    private academicAssistantService: AcademicAssistantService
  ) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['documentId']) {
      this.messages = [];
      this.question = '';
      this.errorMessage = '';
      this.isLoading = false;
    }
  }

  askQuestion(): void {
    const question = this.question.trim();

    if (
      !question ||
      question.length < 3 ||
      this.isLoading ||
      !this.documentId
    ) {
      return;
    }

    // Capture the document ID for this request.
    const documentId = this.documentId;

    this.messages.push({
      role: 'user',
      content: question
    });

    this.question = '';
    this.errorMessage = '';
    this.isLoading = true;

    this.scrollToBottom();

    this.academicAssistantService
      .askQuestion(documentId, question, 5)
      .pipe(
        finalize(() => {
          // Do not let an old request change the new document's state.
          if (this.documentId === documentId) {
            this.isLoading = false;
          }
        })
      )
      .subscribe({

        next: (response: DocumentAnswerResponse) => {
          if (this.documentId !== documentId) {
            return;
          }

          this.messages.push({
            role: 'assistant',
            content: response.answer,
            sources: response.sources || []
          });

          this.scrollToBottom();
        },

        error: (error: HttpErrorResponse) => {
          if (this.documentId !== documentId) {
            return;
          }

          this.errorMessage =
            error.error?.detail ||
            error.error?.message ||
            'Unable to get an answer. Please try again.';

          this.messages.push({
            role: 'assistant',
            content: this.errorMessage,
            sources: []
          });

          this.scrollToBottom();
        }
      });
  }

  onEnter(event: Event): void {
    const keyboardEvent = event as KeyboardEvent;

    // Shift + Enter inserts a new line.
    if (keyboardEvent.shiftKey) {
      return;
    }

    keyboardEvent.preventDefault();

    if (
      !this.isLoading &&
      this.question.trim().length >= 3
    ) {
      this.askQuestion();
    }
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      const element = this.chatMessages?.nativeElement;

      if (element) {
        element.scrollTop = element.scrollHeight;
      }
    });
  }
}
