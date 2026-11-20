
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';

import { AcademicAssistantRoutingModule } from './academic-assistant-routing.module';

import { AssistantPageComponent } from './pages/assistant-page/assistant-page.component';
import { DocumentUploadComponent } from './components/document-upload/document-upload.component';
import { DocumentChatComponent } from './components/document-chat/document-chat.component';
import { FormsModule } from '@angular/forms';

@NgModule({
  declarations: [
    AssistantPageComponent,
    DocumentUploadComponent,
    DocumentChatComponent
  ],
  imports: [
    CommonModule,
    HttpClientModule,
    FormsModule,
    AcademicAssistantRoutingModule
  ]
})
export class AcademicAssistantModule {}
