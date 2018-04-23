#!/usr/bin/env nextflow

replicons_file = file(params.replicons)


process_split{

    input:
        file replicons from replicons_file

    output:
        file "*.fst" into chunks

    beforeScript 'source /home/bneron/Projects/GEM/Integron_Finder/python3/bin/activate'

    """
    integron_split ${replicons}
    """
}

/*
 * myFileChannel = Channel.fromPath( '/path/*b', type: 'dir' )
 */

process_integron_finder{
    input:
        file chunk from chunks

    output:
        path "Integron_Finder_Results_*" into chunk_results

    beforeScript 'source /home/bneron/Projects/GEM/Integron_Finder/python3/bin/activate'

    """
    integron_finder --gbk --pdf ${chunk}
    """
}

Channel
    .from chunk_results
    .collect()
    .set(all_chunk_results)

process_merge{
    publishDir "Integron_Finder_Results_${replicons.simplename}"

    input:
        all_chunk_results

    output:
        "${replicons.simplename}.integrons"

    beforeScript 'source /home/bneron/Projects/GEM/Integron_Finder/python3/bin/activate'

    """
    integron_merge "Integron_Finder_Results_${replicons.simplename}" "${replicons.simplename}" all_chunks
    """
}

workflow.onComplete {
    println ( workflow.success ? "\nDone! Integrons are in --> " : "Oops .. something went wrong" )
}