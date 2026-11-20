import { TestBed } from '@angular/core/testing';

import { AcademicAssistantService } from './academic-assistant.service';

describe('AcademicAssistantService', () => {
  let service: AcademicAssistantService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(AcademicAssistantService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
