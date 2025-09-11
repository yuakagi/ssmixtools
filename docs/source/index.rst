
Ssmixtools Documentation
========================

| This package offers a comprehensive set of tools to construct large clinical datasets from local electronic health record (EHR) storage in Japan.
| Ssmixtools serves as the datapipeline in `our digital-twin framework <https://yuakagi.github.io/Watcher/>`_. 
| However, it proveds a powerful tool for constructing large clinical datasets for any other downstream applications.

| Start with 👉 :doc:`Tutorial <tutorial>`
| GitHub 👉 https://github.com/yuakagi/ssmixtools

Background
========================
| EHR data often presents complex and diverse structures, posing challenges for standardized extraction and cleaning.
| To address these complexities, leveraging a data-standardization scheme such as Health Level Seven (HL7) is essential for developing and distributing robust data-processing solutions for EHR data.

| While HL7 standardization serves as a cornerstone for interoperability, it must also adapt to the significant variations in EHR data structures and requirements across institutions and regions.
| This package has been carefully designed to work seamlessly with Japanese standardized EHR data storage (SS-MIX2), utilizing HL7 messages.  For users working with EHR data outside Japan, the package provides a foundation that could be customized to align with the unique data structures and standards of your region.
| ssmixtools provides an example of how a large clinical dataset could be prepared using a data-standardization scheme.

Supported Data Types
--------------------

  - ADT-12: Outpatient encounter records
  - ADT-22: Admission confirmation records
  - ADT-52: Discharge confirmation records
  - PPR-01: Diagnosis records
  - OMP-01: Prescription order records (excluding injectable agents)
  - OMP-02: Order records for injectable agents
  - OML-11: Laboratory test result records

| Please refer to the original SS-MIX2 implementation guidelines for data details.


.. toctree::
   :maxdepth: 6
   :caption: Documentations:
   :hidden:
  
   Tutorial <tutorial>
   Table Definitions <table_definitions/tables>

.. toctree::
   :maxdepth: 6
   :caption: SSMIXTOOLS API:
   :hidden:

   generated/ssmixtools
