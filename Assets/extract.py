exp=['Erfahrung' ,'Laufbahn','ERFAHRUNG' ," Erfahrungen" ,'LAUFBAHN','Praktische',
                                                           
          'PRAKTISCHE','ERFAHRUNGEN','Praktika','PRAKTIKA' ,
         'Berufserfahrung' ,'EXPERIENCE','Experience' ,'BERÜFSERFAHRUNG','Berufserfahrung']

     for vari in words:        # Match experience word or synonym word from CV and manually 
                                                         created list[exp]  
        if vari in exp:         # if match then find index of that word
          st=words.index(vari)
          start= st+1           #(st+1)for take next word  
                            # get index of experience word of CV
          i = start             #give another variable(i)
     for j in words:                          #create for loop
        if words[i]  not in exp_list:   #if  start index is not in [exp_list(without 
                                                             experience 
                                                                                       word)] 
           i += 1                        #then take next index untill it match the word 
                                                                       of[exp_list]
           end= start+(i-start)               # find end index 
      
 
    

      f_list=[]  #create list
      for item in words[start:end]: #give slicing for take start index and end index
         f_list.append(item)  #append into list
      stringlist = ' '.join(f_list )  #convert into string


      return stringlist

extract_experience('020.pdf')